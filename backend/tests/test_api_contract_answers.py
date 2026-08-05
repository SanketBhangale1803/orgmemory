from app.audit import AuditService
from app.hcag_adapter import HCAGAdapter
from app.ingestion import IngestionService
from app.retrieval import RetrievalService

README = """# Purchase API

## Backend endpoints
- `GET /api/health` — gateway health
- `POST /api/requisition/validate` — policy pre-check
- `POST /api/requisition/draft` — create a requisition draft
- `POST /api/requisition/submit` — submit the draft to SAP
- `POST /api/sap/test-connection` — verify SAP connectivity

Example body:
```json
{"message": "I need 3 laptops for onboarding, cost center 4100, budget $4200."}
```
"""

SERVER = """
class RequestHandler:
    def do_POST(self):
        path = self.path
        if path == "/api/requisition/validate":
            body = parse_body(self)
            message = body.get("message")
            requester = body.get("requester")
            if not message:
                return {"error": "message is required"}

        if path == "/api/requisition/draft":
            body = parse_body(self)
            message = body.get("message")
            requester = body.get("requester")
            if not message:
                return {"error": "message is required"}

        if path == "/api/requisition/submit":
            body = parse_body(self)
            payload = body.get("sap_payload")
            config = body.get("sap_config")
            if not isinstance(payload, dict):
                return {"error": "sap_payload object is required"}

        if path == "/api/sap/test-connection":
            body = parse_body(self)
            config = body.get("sap_config")
            if not isinstance(config, dict):
                return {"error": "sap_config object is required"}
"""

FRONTEND = """
const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000';
const troubleshooting = {"message": "SAP endpoint exists, but it does not allow GET."};
fetch(`${API_BASE}/api/requisition/submit`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ sap_payload: draft.sap_payload, sap_config: sapSession })
});
"""


def _project(graph):
    hcag = HCAGAdapter(graph)
    ingestion = IngestionService(graph, hcag, AuditService())
    project_id = ingestion.create_project("Purchase API")
    ingestion.ingest_item(project_id, "repo_file", "README.md", README)
    ingestion.ingest_item(project_id, "repo_file", "backend/server.py", SERVER)
    ingestion.ingest_item(project_id, "repo_file", "src/main.jsx", FRONTEND)
    ingestion.ingest_item(
        project_id,
        "repo_file",
        "backend/sap_client.py",
        "Check user ID, password/token, auth type, and whether this endpoint allows it.",
    )
    return hcag, project_id


def test_endpoint_and_payload_question_uses_route_contract_not_error_prose(graph):
    hcag, project_id = _project(graph)

    result = RetrievalService(hcag).ask(
        project_id, "What are the endpoints I should send the request to, and what payload?"
    )

    assert result["answer_kind"] == "api_contract"
    assert "POST `/api/requisition/validate`" in result["answer"]
    assert "POST `/api/requisition/draft`" in result["answer"]
    assert "POST `/api/requisition/submit`" in result["answer"]
    assert '"message": "I need 3 laptops' in result["answer"]
    assert '"sap_payload": draftResponse.sap_payload' in result["answer"]
    assert "Check user ID" not in result["answer"]
    assert "does not allow GET" not in result["answer"]
    assert {item["source_title"] for item in result["evidence"]}.issuperset(
        {"README.md", "backend/server.py"}
    )


def test_submit_endpoint_question_returns_only_submit_contract(graph):
    hcag, project_id = _project(graph)

    result = RetrievalService(hcag).ask(
        project_id, "Give me the submit endpoint and its request payload."
    )

    assert "POST `/api/requisition/submit`" in result["answer"]
    assert "/api/requisition/validate" not in result["answer"]
    assert "Pass `sap_payload` returned by the draft endpoint" in result["answer"]


def test_runtime_record_status_abstains_when_only_route_code_is_indexed(graph):
    hcag, project_id = _project(graph)

    result = RetrievalService(hcag).ask(
        project_id, "What is the current status of requisition PR-999?"
    )

    assert result["answer_kind"] == "runtime_record"
    assert result["answer_sufficient"] is False
    assert "does not prove the record's current runtime status" in result["answer"]
    assert result["evidence"] == []


def test_express_routes_and_html_forms_produce_web_contract(graph):
    hcag = HCAGAdapter(graph)
    ingestion = IngestionService(graph, hcag, AuditService())
    project_id = ingestion.create_project("Pinterest")
    ingestion.ingest_item(
        project_id,
        "repo_file",
        "routes/index.js",
        """
const environment = app.get('env');
router.get('/', function (req, res) { res.render('login'); });
router.get('/feed', function (req, res) { res.render('feed'); });
router.get('/profile', isLoggedIn, function (req, res) { res.render('profile'); });
router.post('/upload', isLoggedIn, upload.single('file'), async function (req, res) {
  const caption = req.body.filecaption;
});
router.post('/register', function (req, res) {
  const { username, email, fullname } = req.body;
  User.register({ username, email, fullname }, req.body.password);
});
router.post('/login', passport.authenticate('local'), function (req, res) {});
router.get('/logout', function (req, res) { req.logout(); });
function isLoggedIn(req, res, next) { if (req.isAuthenticated()) return next(); }
""",
    )
    ingestion.ingest_item(
        project_id,
        "repo_file",
        "views/login.ejs",
        """
<form action="/login" method="post">
  <input name="username" />
  <input name="password" type="password" />
</form>
""",
    )
    ingestion.ingest_item(
        project_id,
        "repo_file",
        "views/index.ejs",
        """
<form action="/register" method="post">
  <input name="email" />
  <input name="username" />
  <input name="fullname" />
  <input name="password" type="password" />
</form>
""",
    )

    result = RetrievalService(hcag).ask(
        project_id, "What are the endpoints I should send the request to, and what payload?"
    )

    assert result["answer_kind"] == "api_contract"
    assert "POST `/login`" in result["answer"]
    assert "GET `env`" not in result["answer"]
    assert "application/x-www-form-urlencoded fields: `username`, `password`" in result["answer"]
    assert "POST `/register`" in result["answer"]
    register_contract = (
        result["answer"].split("POST `/register`", 1)[1].split("POST `/upload`", 1)[0]
    )
    assert all(
        f"`{field}`" in register_contract for field in ("email", "username", "fullname", "password")
    )
    assert "POST `/upload`" in result["answer"]
    assert "requires an authenticated session" in result["answer"]
    upload_contract = result["answer"].split("POST `/upload`", 1)[1].split("GET `/`", 1)[0]
    assert "multipart/form-data fields:" in upload_contract
    assert "`file` (binary file)" in upload_contract
    assert "`filecaption`" in upload_contract
    logout_contract = result["answer"].split("GET `/logout`", 1)[1].split("GET `/profile`", 1)[0]
    assert "requires an authenticated session" not in logout_contract
    assert {item["source_title"] for item in result["evidence"]}.issuperset(
        {"routes/index.js", "views/login.ejs", "views/index.ejs"}
    )


def test_route_contract_extraction_is_not_tied_to_one_web_framework(graph):
    hcag = HCAGAdapter(graph)
    ingestion = IngestionService(graph, hcag, AuditService())
    project_id = ingestion.create_project("Polyglot API")
    ingestion.ingest_item(
        project_id,
        "repo_file",
        "api/flask_app.py",
        """@app.route('/jobs', methods=['GET', 'POST'])\ndef jobs(): pass""",
    )
    ingestion.ingest_item(
        project_id,
        "repo_file",
        "src/UsersController.java",
        'class UsersController { @PostMapping("/users") User create() {} }',
    )
    ingestion.ingest_item(
        project_id,
        "repo_file",
        "server/routes.go",
        'router.HandleFunc("/health", healthHandler).Methods("GET")',
    )

    result = RetrievalService(hcag).ask(
        project_id, "List the HTTP endpoints exposed by this project."
    )

    assert "GET `/jobs`" in result["answer"]
    assert "POST `/jobs`" in result["answer"]
    assert "POST `/users`" in result["answer"]
    assert "GET `/health`" in result["answer"]
    assert {item["source_title"] for item in result["evidence"]} == {
        "api/flask_app.py",
        "src/UsersController.java",
        "server/routes.go",
    }
