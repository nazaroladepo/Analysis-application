#!/usr/bin/env bash
set -euo pipefail

echo "🚀 Render start script beginning..."

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo "📄 Environment:"
echo "  - PYTHON_VERSION: $(python --version 2>&1 || echo 'unknown')"
echo "  - PORT: ${PORT:-8000}"

# Optional: run DB migrations on startup (uncomment if/when you rely on Alembic migrations)
# echo \"🗄️  Running database migrations...\"
# cd backend/db
# alembic upgrade head || echo \"⚠️ Alembic migration failed or not configured; continuing\"
# cd \"$PROJECT_ROOT\"

echo \"🌐 Starting uvicorn server...\"
exec uvicorn backend.main:app --host 0.0.0.0 --port \"${PORT:-8080}\" --log-level info

