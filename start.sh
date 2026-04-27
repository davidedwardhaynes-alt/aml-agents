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
    echo "Anthropic API key needed."
    echo ""
    echo "Get one from: https://console.anthropic.com/settings/keys"
    echo "It looks like:  sk-ant-api03-XXXXXXXX..."
    echo ""
    echo "Paste it below. The cursor will NOT move as you type/paste — that is normal."
    echo ""

    KEY=""
    ATTEMPT=0
    while [[ "$KEY" != sk-ant-* ]] && [ $ATTEMPT -lt 3 ]; do
        if [ $ATTEMPT -gt 0 ]; then
            echo ""
            echo "✗ That does not look like an Anthropic API key (must start with 'sk-ant-')."
            echo "  Try again — copy the key fresh from console.anthropic.com."
            echo ""
        fi
        read -r -s -p "API key: " KEY
        echo ""
        ATTEMPT=$((ATTEMPT + 1))
    done

    if [ -z "$KEY" ]; then
        echo "✗ No key entered. Run this script again when ready."
        exit 1
    fi

    if [[ "$KEY" != sk-ant-* ]]; then
        echo ""
        echo "✗ After 3 attempts the key still doesn't start with 'sk-ant-'."
        echo "  Edit ~/dev/amlagents/.env manually, or run this script again."
        exit 1
    fi

    # Preserve any other env vars (e.g. OPENSANCTIONS_API_KEY) when overwriting
    OTHER_VARS=""
    if [ -f .env ]; then
        OTHER_VARS=$(grep -v "^ANTHROPIC_API_KEY=" .env | grep -v "^$" || true)
    fi

    {
        echo "ANTHROPIC_API_KEY=$KEY"
        if [ -n "$OTHER_VARS" ]; then
            echo ""
            echo "$OTHER_VARS"
        fi
    } > .env

    echo ""
    echo "✓ API key saved (preview: ${KEY:0:14}...${KEY: -4})"
    echo ""
fi

echo "Starting the app..."
echo "Your browser will open automatically at http://localhost:8501"
echo "To stop the app later, come back to this Terminal window and press Ctrl+C"
echo ""

source .venv/bin/activate
streamlit run app.py
