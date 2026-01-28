#!/usr/bin/env bash
set -euo pipefail

echo "🚀 Render start script beginning..."

# # Get the backend directory (where this script is located)
# BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# cd "$BACKEND_DIR"

echo "📄 Environment:"
echo "  - PYTHON_VERSION: $(python --version 2>&1 || echo 'unknown')"
echo "  - PORT: ${PORT:-8080}"


echo "🌐 Starting uvicorn server..."
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8080}" --log-level info
