"""
統一的 ZOZO HTML 解析器
同時支援庫存同步和折扣同步，確保SKU生成邏輯100%一致
"""

import re
import hashlib
from collections import defaultdict
from bs4 import BeautifulSoup
import requests

# ✅ 與庫存同步完全一致的顏色映射表
COLOR_MAP = {
    "ブラック": "BLK", "ホワイト": "WHT", "グレー": "GRY", "チャコール": "CHC",
    "ネイビー": "NVY", "ブルー": "BLU", "ライトブルー": "LBL", "ベージュ": "BEI",
    "ブラウン": "BRN", "カーキ": "KHA", "オリーブ": "OLV", "グリーン": "GRN",
    "ダークグリーン": "DGN", "イエロー": "YEL", "マスタード": "MUS", "オレンジ": "ORG",
    "レッド": "RED", "ピンク": "PNK", "パープル": "PUR", "ワイン": "WIN",
    "アイボリー": "IVY", "シルバー": "SLV", "ゴールド": "GLD", "ミント": "MNT",
    "サックス": "SAX", "モカ": "MOC", "テラコッタ": "TER", "ラベンダー": "LAV",
    "スモーキーピンク": "SPK", "スモーキーブルー": "SBL", "スモーキーグリーン": "SGN",
    "杢グレー":"GRY", "スミクロ":"SBLK","ライトベージュ":"LTB","オートミール":"OT","アッシュブラウン":"ATB",
    "グレイッシュベージュ":"GRYB","グレイッシュブルー":"GRYBU"
}

# ✅ 與庫存同步完全一致的顯示映射表
COLOR_DISPLAY_MAP = {
    "ブラック": "黑色", "ホワイト": "白色", "グレー": "灰色", "チャコールグレー": "鐵灰",
    "チャコール": "鐵灰",
    "ネイビー": "深藍", "ブルー": "藍色", "ライトブルー": "天空藍", "ベージュ": "奶茶",
    "ブラウン": "棕色", "カーキ": "卡其", "オリーブ": "軍綠", "グリーン": "綠色",
    "ダークグリーン": "深綠", "イエロー": "黃色", "マスタード": "奶黃", "オレンジ": "橘色",
    "レッド": "紅色", "ピンク": "淡粉", "パープル": "紫色", "ワイン": "酒紅",
    "アイボリー": "象牙白", "シルバー": "銀色", "ゴールド": "金色", "ミント": "薄荷綠",
    "サックス": "丹寧藍", "モカ": "摩卡", "テラコッタ": "TER", "ラベンダー": "薰衣草紫",
    "スモーキーピンク": "SPK", "スモーキーブルー": "SBL", "スモーキーグリーン": "SGN",
    "ライトグレー": "亮灰", "ワインレッド": "酒紅", "サックスブルー": "靛藍" ,"オフホワイト": "米白" ,
    "アッシュグレー": "水泥灰", "ダークネイビー": "深藍","杢グレー":"水泥灰", "スミクロ":"墨黑","ライトベージュ":"奶茶","オートミール":"亮灰","アッシュブラウン":"摩卡棕",
    "グレイッシュベージュ":"卡其灰","グレイッシュブルー":"灰藍"
}

# 庫存狀態映射
stock_status_map = {
    "在庫あり": "10",
    "在庫なし": "0",
    "残り僅か": "3",
    "予約商品": "5",
    "残りわずか": "2",
    "残り1点": "1",
    "残り2点": "2",
    "残り3点": "3",
    "残り4点": "4",
    "残り5点": "5",
    "取り寄せ": "5",
    "予約": "7",
    "予約可能": "7"
}


def sort_sizes(sizes):
    """尺寸排序函數"""
    size_order = ["XXS", "XS", "S", "M", "L", "XL", "XXL", "XXXL", "FREE"]
    def sort_key(size):
        if size in size_order:
            return size_order.index(size)
        return len(size_order)  # 未知尺寸排到最後
    return sorted(sizes, key=sort_key)


class ZozoHtmlParser:
    """統一的ZOZO HTML解析器 - 支援庫存同步和折扣同步"""
    
    def __init__(self, url):
        self.url = url
        self.html = None
        self.soup = None
        self.data = {}
        
    def get_soup(self, html):
        """獲取BeautifulSoup對象"""
        return BeautifulSoup(html, "html.parser")
        
    def fetch_html(self):
        """爬取HTML內容"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(self.url, headers=headers, timeout=30)
            response.raise_for_status()
            self.html = response.text
            self.soup = self.get_soup(self.html)
            return True
        except Exception as e:
            print(f"❌ 爬取HTML失敗: {e}")
            return False
    
    def parse_name_brand(self):
        """解析商品名稱和品牌"""
        try:
            # ✅ 使用與庫存同步完全一致的選擇器
            name_tag = self.soup.select_one(".p-goods-information__heading")
            self.data["name"] = name_tag.get_text(strip=True) if name_tag else ""
            
            # 品牌名稱
            brand_tag = self.soup.select_one(".p-goods-information-brand-link__label")
            self.data["brand"] = brand_tag.get_text(strip=True) if brand_tag else ""
            
        except Exception as e:
            print(f"⚠️ 解析名稱品牌時出錯: {e}")
            self.data["name"] = ""
            self.data["brand"] = ""
    
    def parse_price(self):
        """解析價格信息（折扣同步關注的重點）"""
        try:
            # ✅ 使用與庫存同步完全一致的選擇器
            price_tag = self.soup.select_one(".p-goods-information__price--discount") \
                or self.soup.select_one(".p-goods-information__price") \
                or self.soup.select_one(".price-value")
            
            def extract_price(text):
                if not text:
                    return ""
                match = re.search(r"¥?(\d{3,5})", text.replace(",", ""))
                return match.group(1) if match else ""
            
            self.data["price"] = extract_price(price_tag.get_text(strip=True)) if price_tag else ""
            
            # 原價
            orig_tag = self.soup.select_one(".p-goods-information__proper span")
            orig_price = extract_price(orig_tag.get_text(strip=True)) if orig_tag else ""
            self.data["default_price"] = orig_price
            
            # 折扣百分比
            if self.data["price"] and orig_price and orig_price != self.data["price"]:
                try:
                    discount = round((1 - (int(self.data["price"]) / int(orig_price))) * 100)
                    self.data["discount_ratio"] = f"{discount}%"
                except:
                    self.data["discount_ratio"] = ""
            else:
                # 嘗試直接從頁面獲取折扣百分比
                discount_tag = self.soup.select_one(".p-goods-information-pricedown__rate")
                if discount_tag:
                    match = re.search(r"(\d+)%", discount_tag.get_text())
                    if match:
                        self.data["discount_ratio"] = f"{match.group(1)}%"
                        
            # 🔥 新增：折扣截止時間（折扣同步專用）
            deadline_tag = self.soup.select_one(".p-goods-information-price-detail-type__text")
            if deadline_tag:
                text = deadline_tag.get_text(strip=True)
                match = re.search(r"(\d{1,2})月(\d{1,2})日\s*(\d{1,2}:\d{2})", text)
                if match:
                    month, day, time_str = match.groups()
                    from datetime import datetime
                    now = datetime.now()
                    year = now.year
                    deadline_str = f"{year}-{int(month):02d}-{int(day):02d} {time_str}"
                    self.data["discount_deadline"] = deadline_str
                else:
                    self.data["discount_deadline"] = ""
            else:
                self.data["discount_deadline"] = ""
            
        except Exception as e:
            print(f"⚠️ 解析價格時出錯: {e}")
            self.data["price"] = ""
            self.data["default_price"] = ""
            self.data["discount_ratio"] = ""
            self.data["discount_deadline"] = ""
    
    def parse_stocks(self):
        """解析庫存信息 - 使用與庫存同步完全一致的選擇器"""
        try:
            stock_list = []
            stock_qty_list = []
            raw_colors = {}
            
            # ✅ 使用與庫存同步完全一致的選擇器
            blocks = self.soup.select("dl.p-goods-information-action")
            
            for block in blocks:
                # 獲取顏色
                color_tag = block.select_one("span.p-goods-add-cart__color")
                if not color_tag:
                    continue
                    
                raw_color = color_tag.get_text(strip=True)
                # 轉換顏色顯示
                display_color = COLOR_DISPLAY_MAP.get(raw_color, raw_color)
                raw_colors[display_color] = raw_color
                
                # 獲取尺寸和庫存
                li_tags = block.select("li.p-goods-add-cart-list__item")
                
                for li in li_tags:
                    size = li.get("data-size", "").strip()
                    if not size:
                        continue
                        
                    # 獲取庫存狀態
                    stock_tag = li.select_one(".p-goods-add-cart-stock span:last-child")
                    stock_status = stock_tag.get_text(strip=True) if stock_tag else "尚未擷取到資料"
                    
                    # 轉換庫存數量
                    qty = stock_status_map.get(stock_status, "0")
                    
                    stock_list.append([size, display_color, stock_status])
                    stock_qty_list.append(qty)
            
            self.data["stocks"] = stock_list
            self.data["stocks_qty"] = stock_qty_list
            
            # 生成尺寸順序
            sizes = list({stock[0] for stock in stock_list})
            self.data["sizes"] = sort_sizes(sizes)
            
            # 生成SKU - ✅ 使用完全一致的邏輯
            generated_skus = []
            for (size, color, _) in self.data.get("stocks", []):
                # 使用原始日文颜色生成SKU
                raw_color = raw_colors.get(color, color)
                sku = self.generate_sku(self.data["name"], raw_color, size)
                generated_skus.append({
                    "顏色": color,
                    "尺寸": size,
                    "Freak SKU": sku
                })
            self.data["skus"] = generated_skus
            
        except Exception as e:
            print(f"⚠️ 解析庫存時出錯: {e}")
            self.data["stocks"] = []
            self.data["stocks_qty"] = []
            self.data["sizes"] = []
            self.data["skus"] = []
    
    def parse_images(self):
        """解析圖片信息 - 使用與庫存同步完全一致的選擇器"""
        try:
            # ✅ 優先查找主要商品圖片容器
            main_containers = [
                "ul.p-goods-image-list",
                ".p-goods-images",
                ".goods-images",
                ".product-images"
            ]
            
            image_urls = []
            for container in main_containers:
                section = self.soup.select_one(container)
                if section:
                    img_tags = section.select("img")
                    for img in img_tags:
                        src = img.get("src") or img.get("data-src")
                        if src and src not in image_urls:
                            image_urls.append(src)
                    if image_urls:
                        break
            
            # 如果沒找到，使用通用方法
            if not image_urls:
                img_tags = self.soup.select("img")
                for img in img_tags:
                    src = img.get("src") or img.get("data-src")
                    if src and "goods" in src.lower() and src not in image_urls:
                        image_urls.append(src)
            
            self.data["images"] = image_urls
            self.data["main_image"] = image_urls[0] if image_urls else ""
            
        except Exception as e:
            print(f"⚠️ 解析圖片時出錯: {e}")
            self.data["images"] = []
            self.data["main_image"] = ""
    
    def generate_sku(self, name, color, size):
        """✅ 與庫存同步完全一致的SKU生成邏輯"""
        try:
            # 清理輸入
            clean_product_name = re.sub(r'[^\w\s-]', '', name)
            clean_color = re.sub(r'[^\w]', '', color)
            clean_size = re.sub(r'[^\w]', '', size)
            
            # ✅ 關鍵修正：支援 goods-sale 格式的URL
            product_id_match = re.search(r'/goods(?:-sale)?[/-](\d+)', self.url)
            product_id = product_id_match.group(1) if product_id_match else "UNKNOWN"
            
            # ✅ 使用固定的商品ID + 顏色 + 尺寸生成唯一hash
            unique_string = f"{product_id}-{clean_color}-{clean_size}"
            hash_part = hashlib.md5(unique_string.encode("utf-8")).hexdigest()[:4].upper()
            
            # 生成精確的顏色代碼
            color_code = self.enhanced_color_to_code(color)
            
            # ✅ 最終SKU格式：ZO-[Hash]-[顏色代碼]-[尺寸]
            sku = f"ZO-{hash_part}-{color_code}-{size}"
            
            print(f"🔍 SKU生成：商品ID:{product_id} + {color}+{size} -> hash:{hash_part} -> {sku}")
            return self.clean_sku(sku)
            
        except Exception as e:
            print(f"❌ SKU生成失敗: {e}")
            return f"ZO-ERROR-{color[:3] if color else 'UNK'}-{size}"
    
    def enhanced_color_to_code(self, color):
        """✅ 與庫存同步完全一致的顏色代碼生成"""
        color_map = {
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
            "杢グレー":"GRY","スミクロ":"SBLK","ライトベージュ":"LTB","オートミール":"OT","アッシュブラウン":"ATB","グレイッシュベージュ":"GRYB","グレイッシュブルー":"GRYBU"
        }
        
        # 優先完全匹配
                # 優先完全匹配
        if color in color_map:
            return color_map[color]
        
        # ✅ 關鍵修改：如果沒有完全匹配，直接返回 UNK
        print(f"⚠️ 未映射顏色 '{color}' -> 設為 UNK")
        return "UNK"
        
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
    
    def clean_sku(self, sku):
        """✅ 與庫存同步完全一致的SKU清理"""
        if not sku:
            return ""
        # 移除所有空白字符（包括空格、制表符、換行等）
        cleaned_sku = re.sub(r'\s+', '', str(sku))
        return cleaned_sku
    
    def parse(self, mode="full"):
        """
        執行解析流程
        mode: "full" (完整解析) 或 "discount_only" (只解析折扣相關)
        """
        try:
            # 如果沒有HTML內容，先爬取
            if not self.html:
                if not self.fetch_html():
                    return None
            
            # 確保有soup對象
            if not self.soup:
                self.soup = self.get_soup(self.html)
            
            # 基本解析
            self.parse_name_brand()
            self.parse_price()  # 折扣同步的重點
            
            if mode == "full":
                # 完整解析（庫存同步需要）
                self.parse_images()
                self.parse_stocks()
            elif mode == "discount_only":
                # 只解析必要的信息生成SKU（折扣同步需要）
                self.parse_stocks()  # 仍需要解析以生成SKU
            
            # ✅ 確保返回的data包含url
            self.data["url"] = self.url
            
            return self.data
            
        except Exception as e:
            print(f"❌ 解析過程發生錯誤: {e}")
            return None


# 便利函數 - 向後兼容
def parse_zozo_html(html, url, mode="full"):
    """便利函數 - 支援舊代碼調用"""
    parser = ZozoHtmlParser(url)
    parser.html = html
    parser.soup = parser.get_soup(html)
    return parser.parse(mode)


# 使用範例
if __name__ == "__main__":
    url = "https://zozo.jp/shop/mono-mart/goods-sale/73746072/?did=121049876"
    
    # 完整解析（庫存同步）
    parser = ZozoHtmlParser(url)
    result = parser.parse(mode="full")
    
    if result:
        print(f"✅ 完整解析成功！")
        print(f"商品名稱: {result.get('name', 'N/A')}")
        print(f"品牌: {result.get('brand', 'N/A')}")
        print(f"價格: {result.get('price', 'N/A')}")
        print(f"原價: {result.get('default_price', 'N/A')}")
        print(f"折扣: {result.get('discount_ratio', 'N/A')}")
        print(f"庫存數量: {len(result.get('stocks', []))}")
    
    # 折扣解析（折扣同步）
    discount_result = parser.parse(mode="discount_only")
    
    if discount_result:
        print(f"✅ 折扣解析成功！")
        print(f"折扣百分比: {discount_result.get('discount_ratio', 'N/A')}")
        print(f"折扣截止: {discount_result.get('discount_deadline', 'N/A')}")
