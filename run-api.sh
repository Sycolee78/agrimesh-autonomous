#!/bin/bash
# Run the AgriMesh FastAPI backend

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Set PYTHONPATH
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"

# Check for uvicorn
if ! command -v uvicorn &> /dev/null; then
    echo "Installing uvicorn..."
    pip install uvicorn[standard] fastapi
fi

echo "🚀 Starting AgriMesh API server..."
echo "📍 API will be available at http://localhost:8000"
echo "📚 API docs at http://localhost:8000/docs"
echo ""

uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
