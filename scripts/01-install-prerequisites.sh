#!/usr/bin/env bash
# ============================================
# q7x.ai — Step 1.1: Install Prerequisites
# ============================================
# Target: Ubuntu 24.04 (ARM64 or x86_64)
# Run as: user with sudo access
#
# Installs:
#   - Node.js 22 LTS (via NodeSource)
#   - pnpm (via npm)
#   - Claude Code CLI (via Anthropic installer)
#
# After running this script, you'll need to authenticate
# Claude Code interactively — see 02-authenticate-claude.sh
# ============================================

set -euo pipefail

echo "=== Installing Node.js 22 LTS ==="
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt-get install -y nodejs

echo ""
echo "=== Installing pnpm ==="
sudo npm install -g pnpm

echo ""
echo "=== Installing Claude Code CLI ==="
curl -fsSL https://claude.ai/install.sh | bash

# Add Claude to PATH if not already there
if ! grep -q '\.local/bin' ~/.bashrc; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
fi
export PATH="$HOME/.local/bin:$PATH"

echo ""
echo "=== Verifying installations ==="
echo "Node.js: $(node --version)"
echo "npm:     $(npm --version)"
echo "pnpm:    $(pnpm --version)"
echo "Claude:  $(claude --version)"

echo ""
echo "✅ Prerequisites installed."
echo ""
echo "Next steps:"
echo "  1. Run: source ~/.bashrc"
echo "  2. Run: claude login"
echo "     (Choose subscription auth for personal use, or enter an API key)"
