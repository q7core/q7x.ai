#!/usr/bin/env bash
# 03-deploy-agent.sh — Deploy q7x agent to server
# Run from your local machine: bash scripts/03-deploy-agent.sh
# Prereqs: scripts/01-install-prerequisites.sh and scripts/02-authenticate-claude.sh must be done first.
# The server SSH alias must be configured as q7xvps in ~/.ssh/config.

set -euo pipefail

REMOTE=q7xvps
AGENT_DIR=~/q7x/agent
SERVICE_NAME=q7x-agent

echo "==> Creating agent directory..."
ssh "" "mkdir -p /src"

echo "==> Copying source files..."
scp src/index.ts ":/src/index.ts"
scp package.json  ":/package.json"
scp tsconfig.json ":/tsconfig.json"

echo "==> Installing dependencies..."
ssh "" "cd  && pnpm install --frozen-lockfile 2>&1"

echo "==> Approving native builds (better-sqlite3, esbuild)..."
ssh "" "cd  && echo -e " 
y" | pnpm approve-builds 2>&1 || true"

echo "==> Copying .env (must exist at .private/.env)..."
scp .private/.env ":/.env"

echo ""
echo "IMPORTANT: Before starting the service, accept workspace trust interactively:"
echo "  ssh -t "
echo "  cd  && claude --print hello"
echo "  cd ~/q7x-workspace && claude --print hello"
echo "  exit"
echo ""
read -p "Have you accepted workspace trust in both directories? (y/N) " confirm
[[ "" == "y" ]] || { echo "Aborted. Run the trust step above first."; exit 1; }

echo "==> Installing systemd service..."
scp scripts/q7x-agent.service ":/tmp/q7x-agent.service"
ssh "" "sudo cp /tmp/q7x-agent.service /etc/systemd/system/q7x-agent.service && sudo systemctl daemon-reload"

echo "==> Enabling and starting service..."
ssh "" "sudo systemctl enable  && sudo systemctl restart "

echo "==> Checking status..."
ssh "" "sudo systemctl status  --no-pager | head -8"

echo ""
echo "Done. Test by messaging @q7xai_bot on Telegram."
echo "Logs: ssh  sudo journalctl -u  -f"
