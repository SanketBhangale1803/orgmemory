from pathlib import Path


def test_primary_product_surfaces_use_orgmemory_brand():
    root = Path(__file__).resolve().parents[2]
    for relative in (
        "frontend/app/page.tsx",
        "frontend/components/Nav.tsx",
        "backend/app/main.py",
        "README.md",
        "mcp_server/server.py",
    ):
        content = (root / relative).read_text()
        assert "OrgMemory" in content
    nav = (root / "frontend/components/Nav.tsx").read_text()
    for hidden in ("Approvals", "Simulation", "Reliability queue", "Drift"):
        assert hidden not in nav
