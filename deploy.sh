#!/bin/bash
set -e

# centaur.tools deploy script
# Prevents the wrong-directory deploy problem

PROJ_ROOT="$(cd "$(dirname "$0")" && pwd)"

case "${1:-all}" in
  frontend|front|f)
    echo "Deploying frontend..."
    cd "$PROJ_ROOT"
    npm run build
    fly deploy -a centaur-tools
    ;;
  backend|back|b)
    echo "Deploying backend..."
    cd "$PROJ_ROOT/backend"
    fly deploy -a centaur-api
    ;;
  all|both)
    echo "Deploying frontend..."
    cd "$PROJ_ROOT"
    npm run build
    fly deploy -a centaur-tools

    echo ""
    echo "Deploying backend..."
    cd "$PROJ_ROOT/backend"
    fly deploy -a centaur-api
    ;;
  *)
    echo "Usage: ./deploy.sh [frontend|backend|all]"
    exit 1
    ;;
esac

echo ""
echo "Done. Verifying..."
sleep 3
curl -s -o /dev/null -w "  centaur.tools: %{http_code}\n" "https://centaur.tools/"
curl -s -o /dev/null -w "  API health:    %{http_code}\n" "https://centaur.tools/api/health"
