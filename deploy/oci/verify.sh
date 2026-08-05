#!/usr/bin/env bash
set -euo pipefail

repo_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
cd "${repo_dir}"
set -a
. ./.env.production
set +a

curl -fsS "https://api.${PUBLIC_DOMAIN}/api/health"
curl -fsS "https://api.${PUBLIC_DOMAIN}/.well-known/oauth-authorization-server"
curl -fsS "https://api.${PUBLIC_DOMAIN}/.well-known/oauth-protected-resource"
curl -fsS -o /dev/null "https://app.${PUBLIC_DOMAIN}"

echo
echo "Public app, API, and OAuth discovery checks passed."
