#!/bin/bash
# fix-key.sh — read Anthropic API key from clipboard and save to .env
# Usage:
#   1. Copy your key from console.anthropic.com (use the Copy button)
#   2. Run: ~/dev/amlagents/fix-key.sh

set -e
cd "$(dirname "$0")"

KEY=$(pbpaste)

if [[ "$KEY" != sk-ant-* ]]; then
    echo ""
    echo "✗ Your clipboard does NOT contain an Anthropic API key."
    echo ""
    echo "  Currently in clipboard: '${KEY:0:40}...'"
    echo "  Length: ${#KEY} characters"
    echo ""
    echo "Steps to fix:"
    echo "  1. Open https://console.anthropic.com/settings/keys"
    echo "  2. Click the COPY button next to your key (don't select-and-copy)"
    echo "  3. Run this script again:  ~/dev/amlagents/fix-key.sh"
    echo ""
    exit 1
fi

# Preserve other env vars (e.g. OPENSANCTIONS_API_KEY) when overwriting
OTHER=$(grep -v "^ANTHROPIC_API_KEY=" .env 2>/dev/null | grep -v "^$" || true)
{
    echo "ANTHROPIC_API_KEY=$KEY"
    if [ -n "$OTHER" ]; then
        echo ""
        echo "$OTHER"
    fi
} > .env

echo ""
echo "✓ API key saved to ~/dev/amlagents/.env"
echo "  Preview: ${KEY:0:14}...${KEY: -4}  (${#KEY} chars)"
echo ""
echo "Now restart Streamlit:"
echo "  1. In the Terminal where Streamlit is running, press Ctrl+C"
echo "  2. Run:  ~/dev/amlagents/start.sh"
echo ""
