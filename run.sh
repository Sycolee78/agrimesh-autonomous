#!/usr/bin/env bash
# AgriMesh Autonomous - Run Script
# Works on any computer with Python 3.9+

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Install Python 3.9+ first."
    exit 1
fi

# Create venv if not exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

# Set PYTHONPATH so src imports work
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"

# Run Streamlit
echo "🚀 Starting AgriMesh frontend..."
echo "   Open: http://localhost:8501"
streamlit run frontend/app.py --server.headless true
