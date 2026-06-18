#!/bin/bash
# UAT 部署脚本 — 在 UAT 服务器上执行
# 通常由 GitHub Actions 的 deploy-uat.yml 调用，也可手动执行
set -euo pipefail

APP_DIR="/srv/manju-demo"
USE_LLM="${1:-0}"

echo "[deploy] Starting UAT deployment (USE_LLM=$USE_LLM)"

cd "$APP_DIR"

# 备份当前 db
if [ -f data/manju.db ]; then
  cp data/manju.db "data/manju.db.bak.$(date +%s)"
  echo "[deploy] DB backed up"
fi

# 拉代码
git fetch origin
git reset --hard origin/main
echo "[deploy] Git updated to origin/main"

# 还原 db（如果新版本没有）
if [ ! -f data/manju.db ]; then
  LATEST_BAK=$(ls -t data/manju.db.bak.* 2>/dev/null | head -1)
  if [ -n "$LATEST_BAK" ]; then
    cp "$LATEST_BAK" data/manju.db
    echo "[deploy] DB restored from $LATEST_BAK"
  fi
fi

# 装依赖
source .venv/bin/activate
pip install -r requirements.txt -q
echo "[deploy] Dependencies installed"

# 重新生成环境文件
if [ "$USE_LLM" = "1" ]; then
  cat > .env.runtime << EOF
USE_LLM=1
TOKEN_API_KEY=${TOKEN_API_KEY:-}
TOKEN_API_BASE=${TOKEN_API_BASE:-}
TOKEN_MODEL_NAME=${TOKEN_MODEL_NAME:-}
EOF
  echo "[deploy] .env.runtime written (USE_LLM=1)"
else
  cat > .env.runtime << EOF
USE_LLM=0
EOF
  echo "[deploy] .env.runtime written (USE_LLM=0)"
fi

# 重启
sudo systemctl restart manju-demo
echo "[deploy] systemctl restart issued"

# 健康检查
sleep 3
curl -f http://localhost:8765/api/health && echo "[deploy] Health check passed"
