#!/usr/bin/env bash
set -euo pipefail

echo "🚧 Render build starting..."

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo "📦 Python: installing dependencies from requirements.txt"
pip install --upgrade pip
pip install -r requirements.txt

echo "📦 Frontend: installing npm dependencies and building Vue app"
cd frontend
npm install --legacy-peer-deps
npm run build

echo "✅ Render build completed successfully"

