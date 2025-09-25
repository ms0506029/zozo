#!/bin/bash

echo "📦 開始打包 ZOZO 折扣同步應用程式..."

cd "$(dirname "$0")"

# 主程式名稱
MAIN_SCRIPT="sync_zozo_discounts_gui_enhanced.py"
APP_NAME="ZOZO_Discount_Syncer_New"

# ✅ 確認 geckodriver 存在
if [ ! -f "geckodriver" ]; then
  echo "❗ 錯誤：找不到 geckodriver"
else
  chmod +x geckodriver
fi

# ✅ 確認主程式存在
if [ ! -f "$MAIN_SCRIPT" ]; then
  echo "❗ 錯誤：找不到主程式 $MAIN_SCRIPT"
  exit 1
fi

# ✅ 使用 PyInstaller 打包（與舊版本相同的參數）
echo "🚀 使用 PyInstaller 打包..."
pyinstaller --onedir \
  --windowed \
  --add-data "sku_variant_mapping.xlsx:." \
  --add-data "config.py:." \
  --add-binary "geckodriver:." \
  --add-data "firefox_profile:firefox_profile" \
  --hidden-import selenium \
  --hidden-import beautifulsoup4 \
  --hidden-import pandas \
  --hidden-import openpyxl \
  --hidden-import requests \
  --name "$APP_NAME" \
  "$MAIN_SCRIPT"

# ✅ 修復 macOS App 問題
APP_PATH="dist/$APP_NAME.app"
if [ -d "$APP_PATH" ]; then
  echo "🛠️ 修復 macOS 問題..."
  chmod -R +x "$APP_PATH"
  xattr -cr "$APP_PATH"
  echo "✅ 打包完成！可執行檔位於 $APP_PATH"
else
  echo "⚠️ 打包失敗"
fi

echo ""
echo "[🎯 程序完成]"
