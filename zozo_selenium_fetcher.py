# zozo_selenium_fetcher_optimized.py
"""
優化版 ZOZO Town Selenium 抓取器
專門針對庫存同步進行速度優化
"""

import time
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


class ZozoSeleniumFetcherOptimized:
    """優化版 ZOZO 抓取器 - 專注於庫存資訊"""
    
    def __init__(self, headless=True):
        self.headless = headless
        self.driver = None
        
    def _setup_driver(self):
        """設置優化的 Firefox WebDriver"""
        options = Options()
        if self.headless:
            options.add_argument("--headless")
        
        # 效能優化設定
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        # 禁用不必要的載入以加速
        options.set_preference("javascript.enabled", True)
        options.set_preference("permissions.default.image", 2)  # 禁用圖片
        options.set_preference("permissions.default.stylesheet", 2)  # 禁用CSS
        options.set_preference("dom.ipc.plugins.enabled.libflashplayer.so", False)  # 禁用Flash
        options.set_preference("media.volume_scale", "0.0")  # 禁用音頻
        
        # 設置精簡的 User-Agent
        options.set_preference("general.useragent.override",
                             "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
                             
        # 在現有的 options.set_preference 設定後添加：

        # 更強的反檢測設定
        options.set_preference("dom.webdriver.enabled", False)
        options.set_preference("useAutomationExtension", False)
        options.set_preference("marionette.enabled", False)
        options.set_preference("webdriver.load.strategy", "unstable")

        # 隨機化 User-Agent
        import random
        user_agents = [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"
        ]
        options.set_preference("general.useragent.override", random.choice(user_agents))

        # 添加更多隨機化設定
        options.set_preference("network.http.accept-encoding", "gzip, deflate, br")
        options.set_preference("network.http.accept", "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8")
        
        driver = webdriver.Firefox(options=options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.set_page_load_timeout(15)  # 縮短載入超時
        driver.implicitly_wait(2)         # 縮短隱式等待
        return driver
    
    def fetch_stock_html_only(self, url):
        """
        只抓取庫存相關的 HTML - 極速版本
        預期時間：15-25 秒（相較原來的 2 分鐘）
        """
        print(f"🚀 快速載入：{url}")
        
        try:
            self.driver = self._setup_driver()
            start_time = time.time()
            
            # 載入頁面
            self.driver.get(url)
            print(f"✅ 頁面載入完成 ({time.time() - start_time:.1f}s)")
            
            # 只等待庫存關鍵區域載入 - 大幅縮短等待時間
            try:
                WebDriverWait(self.driver, 8).until(
                    EC.presence_of_element_located((
                        By.CSS_SELECTOR,
                        ".p-goods-information-action, .p-goods-add-cart, .stock-info"
                    ))
                )
                print("✅ 庫存區域已載入")
            except TimeoutException:
                print("⚠️ 庫存區域載入超時，但繼續執行")
            
            # 快速處理 Cookie 彈窗（如有）
            self._quick_handle_popups()
            
            # 輕量級滾動 - 只滾動一次到庫存區域
            self.driver.execute_script("""
                // 快速滾動到商品資訊區域
                var stockSection = document.querySelector('.p-goods-information-action');
                if (stockSection) {
                    stockSection.scrollIntoView({behavior: 'instant'});
                }
            """)
            time.sleep(1)  # 短暫等待
            
            # 獲取 HTML
            html_content = self.driver.page_source
            total_time = time.time() - start_time
            print(f"✅ 抓取完成 ({total_time:.1f}s) - HTML長度: {len(html_content):,}")
            
            # 在 return html_content 之前添加
            print(f"🔍 實際HTML前500字符：")
            print(html_content[:500])
            print(f"🔍 HTML是否包含關鍵字：")
            print(f"  - 'ZOZOTOWN': {'ZOZOTOWN' in html_content}")
            print(f"  - '商品詳細': {'商品詳細' in html_content}")
            print(f"  - 'カートに入れる': {'カートに入れる' in html_content}")
            if 'cloudflare' in html_content.lower() or 'checking your browser' in html_content.lower():
                print("❌ 被Cloudflare反爬蟲攔截！")
            return html_content
            
        except Exception as e:
            print(f"❌ 抓取錯誤：{e}")
            return ""
        finally:
            if self.driver:
                self.driver.quit()
    
    def _quick_handle_popups(self):
        """快速處理彈窗"""
        popup_selectors = [
            "#consentButton",
            ".cookie-consent-button",
            ".close-popup",
            ".modal-close"
        ]
        
        for selector in popup_selectors:
            try:
                element = self.driver.find_element(By.CSS_SELECTOR, selector)
                if element.is_displayed():
                    self.driver.execute_script("arguments[0].click();", element)
                    time.sleep(0.5)
                    break
            except:
                continue


# 便利函數 - 與原有代碼兼容
def fetch_html_from_url_optimized(url, headless=True):
    """優化版的快速抓取函數"""
    fetcher = ZozoSeleniumFetcherOptimized(headless=headless)
    return fetcher.fetch_stock_html_only(url)


# 向後兼容 - 替換原有函數
def fetch_html_from_url(url, headless=True, save_html=False):
    """保持與原代碼的兼容性"""
    return fetch_html_from_url_optimized(url, headless)


if __name__ == "__main__":
    # 測試
    test_url = "https://zozo.jp/shop/beams/goods/74917621/"
    html = fetch_html_from_url_optimized(test_url)
    print(f"測試結果：{'成功' if html else '失敗'}")
