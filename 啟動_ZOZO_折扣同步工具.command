#!/bin/bash
# 啟動_ZOZO_折扣同步工具.command
set -e

# ---- 位置 & 進入專案 ----
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 啟動 ZOZO Town 折扣同步工具..."
echo "📍 工作目錄：$SCRIPT_DIR"

# ---- 啟用 .venv（若存在）----
if [[ -d ".venv" ]]; then
  # macOS/Linux venv
  source ".venv/bin/activate" 2>/dev/null || true
fi

# ---- 檢查 Python 3 ----
if ! command -v python3 &>/dev/null; then
  echo "❗️ 找不到 Python 3，請先安裝 Python"
  echo "下載：https://www.python.org/downloads/"
  read -p "按 Enter 鍵關閉..." && exit 1
fi

# ---- 主程式檔名 ----
MAIN_SCRIPT="sync_zozo_discounts_gui_enhanced.py"
if [[ ! -f "$MAIN_SCRIPT" ]]; then
  echo "❗️ 找不到主程式檔案：$MAIN_SCRIPT（請確認與本腳本同目錄）"
  read -p "按 Enter 鍵關閉..." && exit 1
fi

# ---- 必要檔案檢查 ----
echo "🔍 檢查必要檔案..."
missing_files=()
[[ -f "config.py" ]] || missing_files+=("config.py")
[[ -f "sku_variant_mapping.xlsx" ]] || missing_files+=("sku_variant_mapping.xlsx")
[[ -f "geckodriver" ]] || missing_files+=("geckodriver")

if [ ${#missing_files[@]} -ne 0 ]; then
  echo "❗️ 缺少必要檔案："
  for f in "${missing_files[@]}"; do echo "  - $f"; done
  read -p "按 Enter 鍵關閉..." && exit 1
fi

# ---- geckodriver 權限 ----
if [[ ! -x "geckodriver" ]]; then
  echo "🔧 設定 geckodriver 執行權限..."
  chmod +x geckodriver
fi

# ---- 檢查 Python 依賴（Here-Doc）----
echo "🔍 檢查 Python 依賴..."
python3 <<'PY'
import importlib, sys
mods = [
  "tkinter","pandas","requests","selenium","bs4","openpyxl","hashlib","re","json","lxml"
]
missing = []
for m in mods:
  try:
    importlib.import_module(m)
  except Exception:
    missing.append(m)
if missing:
  print(f"❌ 缺少依賴：{missing}")
  print("請執行：pip3 install pandas requests selenium beautifulsoup4 lxml openpyxl")
  sys.exit(1)
else:
  print("✅ 所有依賴正常")
PY

# ---- 檢查 Firefox ----
if [[ ! -d "/Applications/Firefox.app" ]]; then
  echo "⚠️ 找不到 Firefox，請先安裝：https://www.mozilla.org/firefox/"
  echo "程式仍會嘗試啟動..."
fi

# ---- 取得 Firefox Profile（Here-Doc）----
echo "🔍 檢查 Firefox Profile 設定..."
PROFILE_PATH=$(python3 <<'PY'
import os, glob, sys
base = os.path.expanduser('~/Library/Application Support/Firefox/Profiles')
if os.path.exists(base):
  profiles = glob.glob(os.path.join(base, '*.default*'))
  print(profiles[0] if profiles else 'NOT_FOUND')
else:
  print('NOT_FOUND')
PY
)

if [[ "$PROFILE_PATH" == "NOT_FOUND" ]]; then
  echo "⚠️ 找不到 Firefox Profile；請先開啟 Firefox 產生 Profile，將使用預設設定啟動"
else
  echo "✅ 找到 Firefox Profile: $PROFILE_PATH"
fi

echo ""
echo "🎉 環境檢查完成，正在啟動程式..."
echo "===================================="
echo "💡 使用說明："
echo "1. 確保已在 Firefox 中登入 ZOZO 會員"
echo "2. 確認 config.py 的 EasyStore API 設定"
echo "3. 確認 sku_variant_mapping.xlsx 為最新版本"
echo "===================================="

# ---- 啟動主程式（使用當前環境的 python）----
python3 "$MAIN_SCRIPT"

echo ""
echo "===================================="
echo "程式已結束"
read -p "按 Enter 鍵關閉終端..."
