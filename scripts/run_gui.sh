#!/bin/bash
set -e

# --- Configuration ---
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$PROJECT_ROOT/.venv"
REQUIREMENTS_FILE="$PROJECT_ROOT/pyproject.toml"

echo "=== APA Formatter GUI Launcher ==="
echo "Project Root: $PROJECT_ROOT"

# --- 1. Python Check ---
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 could not be found."
    exit 1
fi
echo "✅ Python 3 found."

# --- 2. Virtual Environment ---
if [ ! -d "$VENV_DIR" ]; then
    echo "⚠️  Virtual environment not found. Creating in '$VENV_DIR'..."
    python3 -m venv "$VENV_DIR"
    echo "✅ Virtual environment created."
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"
echo "✅ Virtual environment activated."

# --- 3. Dependency Installation ---
# Check if apa-formatter is installed (checking import)
if ! python -c "import apa_formatter" &> /dev/null; then
    echo "📦 Installing package in editable mode..."
    pip install -e "$PROJECT_ROOT"
    echo "✅ Package installed."
else
    echo "✅ Dependencies already installed."
fi

# --- 4. Pre-launch Compilation Check ---
echo "� Verifying module compilation..."
COMPILE_OUTPUT=$(python -c "import apa_formatter.gui.app" 2>&1)
COMPILE_EXIT=$?

if [ $COMPILE_EXIT -ne 0 ]; then
    echo ""
    echo "════════════════════════════════════════════════════"
    echo "❌ COMPILATION ERROR — GUI will NOT be launched"
    echo "════════════════════════════════════════════════════"
    echo ""
    echo "$COMPILE_OUTPUT"
    echo ""
    echo "════════════════════════════════════════════════════"
    echo "Fix the errors above and try again."
    exit 1
fi
echo "✅ Module compiled successfully."

# --- 5. Launch GUI ---
echo "🚀 Starting GUI Application..."
if command -v apa-gui &> /dev/null; then
    apa-gui "$@"
else
    python -m apa_formatter.gui.app "$@"
fi
