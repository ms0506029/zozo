# zozo_session.py - 統一SKU生成邏輯版本
"""
ZOZO Town 會員登入與商品資訊抓取模組
使用與批量上架系統完全相同的SKU生成邏輯
"""

import logging
import time
import re
import hashlib
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import sys
import os

# ZOZO Town 相關 URL
ZOZO_LOGIN_URL = "https://zozo.jp/_member/login.html?m=logout&pattern=&from=&integrated="
ZOZO_MYPAGE_URL = "https://zozo.jp/_member/default.html?c=info"

def get_profile_path():
    """獲取 Firefox 配置文件路徑"""
    try:
        # 打包後運行
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, "firefox_profile")
        # 開發環境 - 你的實際路徑
        else:
            return "/Users/chenyanxiang/Library/Application Support/Firefox/Profiles/kq1rlx9n.default-release-1747700335794"
    except:
        # 備用路徑
        return "/Users/chenyanxiang/Library/Application Support/Firefox/Profiles/kq1rlx9n.default-release-1747700335794"

def get_geckodriver_path():
    """獲取 geckodriver 路徑"""
    try:
        # 打包後運行
        if hasattr(sys, '_MEIPASS'):
            if sys.platform.startswith('darwin'):  # macOS
                return os.path.join(sys._MEIPASS, "geckodriver")
            elif sys.platform.startswith('win'):   # Windows
                return os.path.join(sys._MEIPASS, "geckodriver.exe")
        # 開發環境
        else:
            return "/usr/local/bin/geckodriver"
    except:
        return "/usr/local/bin/geckodriver"

# Firefox 設定
PROFILE_PATH = get_profile_path()
GECKODRIVER_BIN = get_geckodriver_path()

# ✅ 統一使用批量上架的增強版顏色對照表
COLOR_MAP = {
    "ブラック": "BLK", "ブラック系": "BLK1", "ブラック系1": "BLK2",
    "ホワイト": "WHT", "ホワイト系": "WHT1", "ホワイト系1": "WHT2",
    "グレー": "GRY", "グレー系": "GRY1", "グレー系1": "GRY2",
    "ネイビー": "NVY", "ネイビー系": "NVY1", "ネイビー系1": "NVY2",
    "ブルー": "BLU", "ブルー系": "BLU1", "ブルー系1": "BLU2",
    "ブラウン": "BRN", "ブラウン系": "BRN1", "ブラウン系1": "BRN2",
    "ベージュ": "BEI", "ベージュ系": "BEI1", "ベージュ系1": "BEI2",
    "レッド": "RED", "レッド系": "RED1", "レッド系1": "RED2",
    "ピンク": "PNK", "ピンク系": "PNK1", "ピンク系1": "PNK2",
    "グリーン": "GRN", "グリーン系": "GRN1", "グリーン系1": "GRN2",
    "イエロー": "YEL", "イエロー系": "YEL1", "イエロー系1": "YEL2",
    "パープル": "PUR", "パープル系": "PUR1", "パープル系1": "PUR2",
    "オレンジ": "ORG", "オレンジ系": "ORG1", "オレンジ系1": "ORG2",
    "カーキ": "KHA", "カーキ系": "KHA1", "カーキ系1": "KHA2",
    "ライトブルー": "LBL", "チャコール": "CHC", "オリーブ": "OLV",
    "ダークグリーン": "DGN", "マスタード": "MUS", "ワイン": "WIN",
    "アイボリー": "IVY", "シルバー": "SLV", "ゴールド": "GLD", "ミント": "MNT",
    "サックス": "SAX", "モカ": "MOC", "テラコッタ": "TER", "ラベンダー": "LAV",
    "スモーキーピンク": "SPK", "スモーキーブルー": "SBL", "スモーキーグリーン": "SGN"
}

# 全局瀏覽器實例
_driver = None

# ✅ 統一使用批量上架的增強版SKU生成邏輯
def generate_enhanced_sku(product_name, color, size, url):
    """✅ 與批量上架系統完全一致的SKU生成邏輯"""
    import re
    
    # 🔍 商品ID提取（與批量上架一致）
    if not url:
        product_id = "UNKNOWN"
    elif len(url) < 10:
        product_id = "UNKNOWN"
    else:
        # 使用相同的正則表達式模式
        patterns = [
            r'/goods(?:-sale)?[/-](\d+)',
            r'/goods[/-](?:sale/)?(\d+)',
            r'/goods-sale/(\d+)',
            r'/(\d+)/',
            r'goods.*?(\d+)',
            r'(\d{8})',  # 直接匹配8位數字
        ]
        
        product_id = "UNKNOWN"
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                product_id = match.group(1)
                break
    
    # 生成SKU
    clean_color = re.sub(r'[^\w]', '', color)
    clean_size = re.sub(r'[^\w]', '', size)
    unique_string = f"{product_id}-{clean_color}-{clean_size}"
    hash_part = hashlib.md5(unique_string.encode("utf-8")).hexdigest()[:4].upper()
    color_code = enhanced_color_to_code(color)
    sku = f"ZO-{hash_part}-{color_code}-{size}"
    
    return clean_sku(sku)

def enhanced_color_to_code(color):
    """✅ 與批量上架系統完全一致的顏色代碼生成"""
    # 優先完全匹配
    if color in COLOR_MAP:
        return COLOR_MAP[color]
    
    # 如果沒有完全匹配，使用完整顏色名稱的縮寫
    # 移除常見後綴
    clean_color = re.sub(r'[系\d]', '', color)
    
    # 生成3位縮寫
    if len(clean_color) >= 3:
        code = clean_color[:3].upper()
    else:
        code = color[:3].upper()
    
    # 確保代碼唯一性
    if '系' in color:
        if '1' in color:
            code += '2'
        else:
            code += '1'
    
    return code

def clean_sku(sku):
    """✅ 與批量上架系統完全一致的SKU清理"""
    if not sku:
        return ""
    # 移除所有空白字符（包括空格、制表符、換行等）
    cleaned_sku = re.sub(r'\s+', '', str(sku))
    return cleaned_sku

# ⚠️ 保留舊函數名稱以確保向後兼容
def color_to_code(color):
    """向後兼容函數 - 內部使用新的enhanced邏輯"""
    return enhanced_color_to_code(color)

def generate_zozo_sku(product_name, color, size, url):
    """向後兼容函數 - 內部使用新的enhanced邏輯"""
    return generate_enhanced_sku(product_name, color, size, url)

def setup_zozo_session():
    """啟動並返回全局唯一的 Firefox WebDriver (帶 profile)"""
    global _driver
    if _driver:
        return _driver

    options = Options()
    options.profile = PROFILE_PATH
    # 強制覆蓋Profile設定
    options.set_preference("javascript.enabled", True)
    options.set_preference("permissions.default.image", 2)
    options.set_preference("dom.webdriver.enabled", False)
    options.headless = False  # 可以改為 True 以隱藏瀏覽器視窗
    
    # 添加關鍵設定解決 SSL 問題
    options.accept_insecure_certs = True
    options.set_preference("security.enterprise_roots.enabled", True)
    options.set_preference("security.cert_pinning.enforcement_level", 0)
    options.set_preference("security.ssl.enable_ocsp_stapling", False)
    
    # 隱藏自動化標識，避免被網站檢測
    options.set_preference("dom.webdriver.enabled", False)
    options.set_preference("useAutomationExtension", False)
    
    # 設定用戶代理以避免檢測
    options.set_preference("general.useragent.override",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:91.0) Gecko/20100101 Firefox/91.0")
    
    service = Service(executable_path=GECKODRIVER_BIN)
    driver = webdriver.Firefox(service=service, options=options)
    driver.set_page_load_timeout(30)
    
    # 訪問 ZOZO Town 會員頁面以確認登入狀態
    try:
        logging.info(f"正在載入 ZOZO 會員頁面確認登入狀態: {ZOZO_MYPAGE_URL}")
        driver.get(ZOZO_MYPAGE_URL)
        time.sleep(3)  # 等待頁面加載
        
        # 檢查是否成功登入 - ZOZO 的會員頁面特徵
        page_source = driver.page_source
        if any(keyword in page_source for keyword in ["マイページ", "ログアウト", "お気に入り", "購入履歴"]):
            logging.info("✓ 已確認登入 ZOZO Town 會員")
        else:
            logging.warning("⚠️ 可能未成功登入 ZOZO Town 會員，請先手動登入")
            # 如果未登入，可以嘗試跳轉到登入頁面
            driver.get(ZOZO_LOGIN_URL)
            time.sleep(2)
    except Exception as e:
        logging.error(f"訪問會員頁面時出錯: {e}")
    
    _driver = driver
    logging.info("✅ Firefox 瀏覽器已啟動 (使用已登入的 profile)")
    return driver

def cleanup_zozo_session():
    """關閉瀏覽器，釋放資源"""
    global _driver
    if _driver:
        try:
            _driver.quit()
            logging.info("🗑️ Firefox 瀏覽器已關閉")
        except:
            pass
        _driver = None

def get_zozo_product_info(url):
    try:
        from zozo_selenium_fetcher import fetch_html_from_url_optimized
        test_html = fetch_html_from_url_optimized(url, headless=True)
        
        if test_html and len(test_html) > 10000:
            # 如果優化版能獲取到完整HTML，直接使用
            print(f"使用優化版抓取器獲取HTML成功，長度: {len(test_html)}")
            
            from zozo_html_parser import ZozoHtmlParser
            parser = ZozoHtmlParser(url)
            parser.html = test_html
            parser.soup = parser.get_soup(test_html)
            parsed_data = parser.parse()
            
            if parsed_data and parsed_data.get("name"):
                # 轉換為 get_zozo_product_info 期望的格式
                result = {
                    'product_name': parsed_data.get('name', ''),
                    'color': 'ブラック',  # 預設值
                    'size': 'FREE',      # 預設值
                    'original_price': int(parsed_data.get('default_price', 0)) if parsed_data.get('default_price') else 0,
                    'discounted_price': int(parsed_data.get('price', 0)) if parsed_data.get('price') else 0,
                    'discount_pct': 0,
                    'sizes': parsed_data.get('sizes', []),
                    'stocks': parsed_data.get('stocks', []),
                    'skus': [sku_info.get('Freak SKU', '') for sku_info in parsed_data.get('skus', [])],
                    'discount_deadline': ''
                }
                
                # 計算折扣百分比
                if result['original_price'] > result['discounted_price'] > 0:
                    result['discount_pct'] = round(
                        (result['original_price'] - result['discounted_price']) / result['original_price'] * 100
                    )
                
                print(f"優化版解析成功: {result['product_name'][:30]}...")
                return result
    except Exception as e:
        print(f"優化版抓取失敗，回退到原方法: {e}")
    """
    用 Selenium+Firefox profile 抓取 ZOZO 商品資訊（會員折扣）
    返回: {
        'product_name': str,
        'color': str,
        'size': str,
        'original_price': int,
        'discounted_price': int,
        'discount_pct': int,
        'sizes': list,
        'stocks': list,
        'skus': list,
        'discount_deadline': str
    }
    """
    
    
    driver = setup_zozo_session()
    logging.info(f"🔥 載入 ZOZO 商品頁面: {url}")
    
    try:
        # 導航到商品頁面
        driver.get(url)

        # 使用與庫存系統一致的智能等待邏輯
        print("等待內容載入...")
        time.sleep(3)  # 基本等待

        # 檢查關鍵元素是否載入
        try:
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.common.by import By
            
            WebDriverWait(driver, 8).until(
                EC.any_of(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".p-goods-information-action")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".p-goods-add-cart")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, "li.p-goods-add-cart-list__item")),
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".p-goods-information__heading"))
                )
            )
            print("找到商品頁面元素")
        except:
            print("未找到特定元素，繼續處理...")

        # 觸發懶載入
        try:
            driver.execute_script("window.scrollTo(0, 1000);")
            time.sleep(1)
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
        except:
            pass
        # 最終確認頁面完整性
        try:
            page_source_check = driver.page_source
            if len(page_source_check) < 5000:
                print(f"⚠️ 頁面內容過短 ({len(page_source_check)} 字符)，額外等待...")
                time.sleep(3)
                
            # 檢查是否包含商品關鍵內容
            if "p-goods-information" not in page_source_check:
                print("⚠️ 未找到商品信息區域，嘗試重新載入...")
                driver.refresh()
                time.sleep(5)
        except Exception as e:
            print(f"頁面檢查出錯: {e}")
        
        # 檢查頁面是否成功加載
        page_source = driver.page_source
        if any(keyword in page_source for keyword in ["商品詳細", "カートに入れる", "お気に入り", "ZOZOTOWN"]):
            logging.info("✓ ZOZO 商品頁面加載成功")
        else:
            logging.warning("⚠️ 商品頁面可能未正確加載，將嘗試重新加載")
            driver.refresh()
            time.sleep(5)
            page_source = driver.page_source
        
        # 使用 BeautifulSoup 解析頁面
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # 初始化返回數據
        result = {
            'product_name': '',
            'color': 'ブラック',
            'size': 'FREE',
            'original_price': 0,
            'discounted_price': 0,
            'discount_pct': 0,
            'sizes': [],
            'stocks': [],
            'skus': [],
            'discount_deadline': ''
        }
        
        # 1. 獲取產品名稱 - 使用正確的 ZOZO 選擇器
        name_tag = soup.select_one(".p-goods-information__heading")
        if name_tag:
            result['product_name'] = name_tag.get_text(strip=True)
            logging.info(f"找到商品名稱: {result['product_name'][:50]}...")
        else:
            # 備用選擇器
            title_tag = soup.find('title')
            if title_tag:
                title_text = title_tag.get_text(strip=True)
                if 'ZOZOTOWN' in title_text:
                    clean_title = title_text.replace('ZOZOTOWN', '').replace('|', '').strip()
                    if clean_title:
                        result['product_name'] = clean_title
                        logging.info(f"從 title 獲取商品名稱: {clean_title[:50]}...")
        
        # 2. 獲取價格資訊 - 使用正確的 ZOZO 選擇器
        def extract_price(text):
            if not text:
                return 0
            match = re.search(r"\d[\d,]*", text)
            return int(match.group().replace(",", "")) if match else 0
        
        # ZOZO 折扣價格
        price_tag = soup.select_one(".p-goods-information__price--discount")
        if price_tag:
            result['discounted_price'] = extract_price(price_tag.get_text())
            logging.info(f"找到折扣價: ¥{result['discounted_price']:,}")
        
        # ZOZO 原價
        orig_tag = soup.select_one(".p-goods-information__proper span")
        if orig_tag:
            result['original_price'] = extract_price(orig_tag.get_text())
            logging.info(f"找到原價: ¥{result['original_price']:,}")
        
        # 如果沒有折扣價但有原價，設為相同
        if result['original_price'] > 0 and result['discounted_price'] == 0:
            result['discounted_price'] = result['original_price']
        
        # 如果都沒有，嘗試通用方法
        if result['discounted_price'] == 0 and result['original_price'] == 0:
            price_selectors = ['.price', '[class*="price"]']
            for selector in price_selectors:
                price_tags = soup.select(selector)
                for tag in price_tags:
                    price = extract_price(tag.get_text())
                    if price > 0:
                        result['discounted_price'] = price
                        result['original_price'] = price
                        break
                if result['discounted_price'] > 0:
                    break
        
        # 3. 獲取顏色和尺寸資訊 - 使用正確的 ZOZO 結構
        stocks = []
        
        # 使用正確的 ZOZO 庫存區塊選擇器
        blocks = soup.select("dl.p-goods-information-action")
        logging.info(f"找到 {len(blocks)} 個庫存區塊")
        
        for block in blocks:
            # 獲取顏色
            color_tag = block.select_one("span.p-goods-add-cart__color")
            if not color_tag:
                continue
            color_jp = color_tag.get_text(strip=True)
            
            # 獲取該顏色的所有尺寸
            li_tags = block.select("li.p-goods-add-cart-list__item")
            for li in li_tags:
                size = li.get("data-size", "").strip()
                if size:
                    stocks.append((size, color_jp))
        
        # 設定預設值和列表
        if stocks:
            result['size'], result['color'] = stocks[0]
            result['sizes'] = list(set([stock[0] for stock in stocks]))
            result['stocks'] = stocks
        else:
            # 備用方法 - 嘗試其他選擇器
            color_selectors = ['.color-option', '[class*="color"]']
            size_selectors = ['.size-option', '[class*="size"]', 'button[data-size]']
            
            colors = []
            sizes = []
            
            for selector in color_selectors:
                color_tags = soup.select(selector)
                for tag in color_tags:
                    text = tag.get_text(strip=True)
                    if text and len(text) < 20:
                        colors.append(text)
            
            for selector in size_selectors:
                size_tags = soup.select(selector)
                for tag in size_tags:
                    text = tag.get_text(strip=True)
                    if text and len(text) < 10:
                        sizes.append(text)
            
            if colors:
                result['color'] = colors[0]
            if sizes:
                result['size'] = sizes[0]
                result['sizes'] = list(set(sizes))
                
            # 生成基本庫存組合
            color_list = colors[:2] if colors else [result['color']]
            size_list = result['sizes'] if result['sizes'] else [result['size']]
            
            for color in color_list:
                for size in size_list:
                    stocks.append((size, color))
            
            result['stocks'] = stocks
        
        # 4. 生成庫存組合和 SKU - ✅ 使用統一的SKU生成邏輯
        skus = []
        
        for size, color in result['stocks']:
            if result['product_name']:  # 只有在有商品名稱時才生成 SKU
                sku = generate_enhanced_sku(result['product_name'], color, size, url)
                skus.append(sku)
        
        result['skus'] = skus
        
        # 5. 獲取折扣截止時間 - 使用正確的選擇器
        deadline_tag = soup.select_one(".p-goods-information-price-detail-type__text")
        if deadline_tag:
            text = deadline_tag.get_text(strip=True)
            match = re.search(r"(\d{1,2})月(\d{1,2})日\s*(\d{1,2}:\d{2})", text)
            if match:
                month, day, time_str = match.groups()
                from datetime import datetime
                now = datetime.now()
                year = now.year
                deadline_str = f"{year}-{int(month):02d}-{int(day):02d} {time_str}"
                result['discount_deadline'] = deadline_str
                logging.info(f"找到折扣截止時間: {deadline_str}")
        
        # 6. 計算或獲取折扣百分比
        if result['original_price'] > result['discounted_price'] > 0:
            result['discount_pct'] = round(
                (result['original_price'] - result['discounted_price']) / result['original_price'] * 100
            )
        else:
            # 嘗試直接從頁面獲取折扣百分比
            discount_tag = soup.select_one(".p-goods-information-pricedown__rate")
            if discount_tag:
                match = re.search(r"(\d+)%", discount_tag.get_text())
                if match:
                    result['discount_pct'] = int(match.group(1))
        
        # 7. 記錄解析結果
        logging.info(f"✅ ZOZO 解析結果:")
        logging.info(f"   商品名稱: {result['product_name'][:50]}...")
        logging.info(f"   顏色: {result['color']}")
        logging.info(f"   尺寸: {result['size']}")
        logging.info(f"   原價: ¥{result['original_price']:,}")
        logging.info(f"   售價: ¥{result['discounted_price']:,}")
        logging.info(f"   折扣: {result['discount_pct']}%")
        logging.info(f"   所有尺寸: {result['sizes']}")
        logging.info(f"   生成 SKU 數: {len(skus)}")
        
        # 檢查解析是否成功
        if not result['product_name']:
            logging.warning("⚠️ 未能獲取商品名稱，可能需要調整選擇器")
        if result['discounted_price'] == 0:
            logging.warning("⚠️ 未能獲取價格資訊，可能需要調整選擇器")
        
        return result
        
    except Exception as e:
        logging.error(f"❌ 獲取 ZOZO 商品資訊出錯: {e}")
        import traceback
        logging.error(traceback.format_exc())
        
        # 返回最小的數據結構，避免後續處理出錯
        return {
            'product_name': '',
            'color': 'ブラック',
            'size': 'FREE',
            'original_price': 0,
            'discounted_price': 0,
            'discount_pct': 0,
            'sizes': [],
            'stocks': [],
            'skus': [],
            'discount_deadline': ''
        }

def test_zozo_session():
    """測試 ZOZO 會話是否正常工作"""
    try:
        driver = setup_zozo_session()
        logging.info("🧪 測試 ZOZO 會話...")
        
        # 測試訪問 ZOZO 首頁
        driver.get("https://zozo.jp/")
        time.sleep(3)
        
        if "ZOZOTOWN" in driver.page_source:
            logging.info("✅ ZOZO 會話測試成功")
            return True
        else:
            logging.error("❌ ZOZO 會話測試失敗")
            return False
            
    except Exception as e:
        logging.error(f"❌ ZOZO 會話測試出錯: {e}")
        return False
    finally:
        cleanup_zozo_session()

if __name__ == "__main__":
    # 簡化測試 - 只測試核心功能
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    print("🧪 ZOZO Session 統一SKU邏輯測試")
    print("=" * 50)
    
    # 測試商品資訊抓取
    test_url = "https://zozo.jp/shop/mono-mart/goods/73746072/?did=121049876&rid=1006"
    
    try:
        print("正在測試商品資訊抓取...")
        product_info = get_zozo_product_info(test_url)
        
        if product_info['product_name']:
            print("✅ 測試成功！")
            print(f"商品名稱: {product_info['product_name'][:50]}...")
            print(f"價格: ¥{product_info['original_price']:,} → ¥{product_info['discounted_price']:,}")
            print(f"折扣: {product_info['discount_pct']}%")
            print(f"顏色尺寸組合: {len(product_info['stocks'])} 個")
            print(f"生成 SKU: {len(product_info['skus'])} 個")
            
            # 顯示統一SKU生成的結果
            if product_info['skus']:
                print(f"\n🔍 統一SKU生成驗證:")
                for i, sku in enumerate(product_info['skus'][:3]):
                    print(f"   SKU {i+1}: {sku}")
                print(f"   格式: ZO-{hash}-{color_code}-{size}")
        else:
            print("❌ 測試失敗：無法獲取商品名稱")
            print("可能需要調整 HTML 選擇器")
            
    except Exception as e:
        print(f"❌ 測試出錯: {e}")
        
    finally:
        cleanup_zozo_session()
        print("\n測試完成！")
