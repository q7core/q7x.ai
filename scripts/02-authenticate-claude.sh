#!/usr/bin/env bash
# ============================================
# q7x.ai — Step 1.2: Authenticate Claude Code
# ============================================
# This step is interactive — it requires a browser.
#
# Two authentication options:
#
# Option A: Subscription auth (personal use)
#   claude login
#   - Opens a browser URL for OAuth
#   - Usage counts against your Claude Max plan
#   - No per-token costs
#
# Option B: API key auth (business/production use)
#   export ANTHROPIC_API_KEY=sk-ant-...
#   - Pay-per-token billing
#   - Store key in .env, never in code
#
# For headless/remote servers (no browser), claude login
# will print a URL and an auth code. Open the URL on any
# browser, complete the login, and enter the code back
# in the terminal.
# ============================================

set -euo pipefail

export PATH="$HOME/.local/bin:$PATH"

echo "=== Claude Code Authentication ==="
echo ""
echo "Choose your auth method:"
echo "  1) Subscription (personal use, no per-token cost)"
echo "  2) API key (business use, pay-per-token)"
echo ""
read -p "Enter 1 or 2: " choice

case $choice in
    1)
        echo ""
        echo "Starting Claude login..."
        echo "You'll get a URL to open in your browser."
        echo "If on a remote server, copy the URL and open it locally."
        echo ""
        claude login
        ;;
    2)
        echo ""
        read -p "Enter your Anthropic API key: " api_key
        echo ""
        echo "Add this to your .env file:"
        echo "  ANTHROPIC_API_KEY=$api_key"
        echo ""
        echo "The Agent SDK will pick it up from the environment."
        ;;
    *)
        echo "Invalid choice. Run this script again."
        exit 1
        ;;
esac

echo ""
echo "=== Verifying authentication ==="
claude --version
echo "✅ Claude Code ready."
