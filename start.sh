#!/bin/bash
# AML Agents — one-command setup and launch
# Run this from Terminal:  ~/dev/amlagents/start.sh

set -e
cd "$(dirname "$0")"

echo ""
echo "============================================"
echo "  AML Agents — STR Narrative Drafter"
echo "============================================"
echo ""

# Check if .env exists and has a real key
NEEDS_KEY=true
if [ -f .env ] && grep -q "ANTHROPIC_API_KEY=sk-ant-" .env && ! grep -q "sk-ant-paste-your-key-here" .env; then
    NEEDS_KEY=false
fi

if [ "$NEEDS_KEY" = true ]; then
    echo "First-time setup — your API key is needed."
    echo ""
    echo "Paste your Anthropic API key below."
    echo "(The cursor will NOT move as you type — that is normal, for security)"
    echo ""
    read -r -s -p "API key: " KEY
    echo ""
    echo ""

    if [ -z "$KEY" ]; then
        echo "✗ No key entered. Run this script again when ready."
        exit 1
    fi

    if [[ "$KEY" != sk-ant-* ]]; then
        echo "⚠  Warning: key does not start with 'sk-ant-'. Anthropic keys usually do."
        echo "   Continuing anyway. If the app errors, run this script again with the right key."
        echo ""
    fi

    echo "ANTHROPIC_API_KEY=$KEY" > .env
    echo "✓ API key saved."
    echo ""
fi

echo "Starting the app..."
echo "Your browser will open automatically at http://localhost:8501"
echo "To stop the app later, come back to this Terminal window and press Ctrl+C"
echo ""

source .venv/bin/activate
streamlit run app.py
