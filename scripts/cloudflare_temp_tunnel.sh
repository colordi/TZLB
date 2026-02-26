#!/usr/bin/env bash
set -euo pipefail

PORT="${1:-5001}"
LOCAL_URL="http://127.0.0.1:${PORT}"

if ! command -v cloudflared >/dev/null 2>&1; then
  echo "未检测到 cloudflared，请先安装。"
  echo "macOS 可用: brew install cloudflare/cloudflare/cloudflared"
  echo "Linux 可参考 Cloudflare 官方文档安装。"
  exit 1
fi

echo "正在启动临时隧道 -> ${LOCAL_URL}"
cloudflared tunnel --url "${LOCAL_URL}" --no-autoupdate
