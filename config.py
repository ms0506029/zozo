# config.py
import os, sys

if getattr(sys, "frozen", False):
    # PyInstaller one-dir：資源放在 _MEIPASS
    RESOURCE_DIR = sys._MEIPASS
    # 執行時工作目錄：使用者點 app 的當前目錄
    WORK_DIR = os.getcwd()
else:
    RESOURCE_DIR = os.path.dirname(os.path.abspath(__file__))
    WORK_DIR    = RESOURCE_DIR

# EasyStore API
STORE_URL = "takemejapan"
ACCESS_TOKEN = "f232b671b6cb3bb8151c23c2bd39129a"
API_HEADERS = {
    "EasyStore-Access-Token": ACCESS_TOKEN,
    "Content-Type": "application/json"
}
BASE_API = f"https://{STORE_URL}.easy.co/api/3.0"
