"""
ZOZO折扣同步專用處理器
完全使用與庫存同步系統一致的SKU生成邏輯
專注於價格和折扣信息的同步
"""

import hashlib
import re
from zozo_html_parser import ZozoHtmlParser


class ZozoDiscountSyncProcessor:
    """ZOZO折扣同步處理器 - 使用與庫存同步完全一致的邏輯"""
    
    def __init__(self):
        """初始化處理器"""
        self.parser = None
        
    def process_product_for_discount_sync(self, url, html_content=None):
        """
        處理單一商品的折扣同步
        
        Args:
            url: 商品URL
            html_content: HTML內容（可選，如果不提供會重新爬取）
            
        Returns:
            dict: 包含折扣信息和SKU的數據
        """
        try:
            # ✅ 直接導入並使用 selenium fetcher
            from zozo_selenium_fetcher import fetch_html_from_url_optimized
            
            # 獲取HTML內容
            if not html_content:
                print(f"🔍 正在獲取商品頁面: {url}")
                html_content = fetch_html_from_url_optimized(url, headless=True)
                
                if not html_content or len(html_content) < 1000:
                    return {"error": "無法獲取有效的HTML內容", "variants": []}
            
            # ✅ 正確初始化解析器
            self.parser = ZozoHtmlParser(url)
            self.parser.html = html_content
            self.parser.soup = self.parser.get_soup(html_content)
            
            # 解析商品數據（折扣模式）
            parsed_data = self.parser.parse(mode="discount_only")
            
            if not parsed_data:
                return {"error": "解析商品數據失敗", "variants": []}
            
            # 生成折扣同步所需的數據結構
            sync_data = self.build_discount_sync_data(parsed_data, url)
            
            return sync_data
            
        except Exception as e:
            print(f"❌ 處理商品失敗: {e}")
            return {"error": str(e), "variants": []}
    
    def build_discount_sync_data(self, parsed_data, url):
        """
        構建折扣同步所需的數據結構
        
        Args:
            parsed_data: 解析後的商品數據
            url: 商品URL
            
        Returns:
            dict: 折扣同步數據
        """
        result = {
            "product_name": parsed_data.get("name", ""),
            "brand": parsed_data.get("brand", ""),
            "price": parsed_data.get("price", ""),
            "default_price": parsed_data.get("default_price", ""),
            "discount_ratio": parsed_data.get("discount_ratio", ""),
            "discount_deadline": parsed_data.get("discount_deadline", ""),
            "url": url,
            "variants": [],
            "total_variants": 0,
            "successful_matches": 0,
            "failed_matches": 0,
            "main_sku": "",  # 主要SKU（用於查找Easy Store商品）
            "discount_percentage": 0  # 純數字折扣百分比
        }
        
        try:
            # 提取折扣百分比數字
            discount_ratio = parsed_data.get("discount_ratio", "")
            if discount_ratio:
                match = re.search(r'(\d+)', discount_ratio)
                if match:
                    result["discount_percentage"] = int(match.group(1))
            
            # 獲取變體數據
            stocks = parsed_data.get("stocks", [])
            
            if not stocks:
                return result
            
            # 處理每個變體
            for i, stock_info in enumerate(stocks):
                if len(stock_info) < 3:
                    continue
                    
                size = stock_info[0]
                color = stock_info[1]
                status = stock_info[2]
                
                # ✅ 使用與庫存同步完全一致的SKU生成邏輯
                sku = self.generate_sku_like_inventory_system(
                    product_name=parsed_data.get("name", ""),
                    color=color,
                    size=size,
                    url=url
                )
                
                variant_data = {
                    "size": size,
                    "color": color,
                    "status": status,
                    "sku": sku,
                    "freak_sku": sku,  # 保持一致性
                    "easystore_sku": sku,
                    "original_price": int(parsed_data.get("default_price", 0)) if parsed_data.get("default_price") else 0,
                    "discounted_price": int(parsed_data.get("price", 0)) if parsed_data.get("price") else 0,
                    "discount_percentage": result["discount_percentage"]
                }
                
                result["variants"].append(variant_data)
                result["total_variants"] += 1
                
                # 設置主要SKU（使用第一個變體的SKU）
                if i == 0:
                    result["main_sku"] = sku
            
            print(f"🔍 折扣同步數據構建完成:")
            print(f"   商品名稱: {result['product_name']}")
            print(f"   折扣百分比: {result['discount_percentage']}%")
            print(f"   總變體數: {result['total_variants']}")
            print(f"   主要SKU: {result['main_sku']}")
            print(f"   URL: {url}")
            
            return result
            
        except Exception as e:
            print(f"❌ 構建折扣同步數據失敗: {e}")
            result["error"] = str(e)
            return result
    
    def generate_sku_like_inventory_system(self, product_name, color, size, url):
        """
        ✅ 使用與庫存同步系統完全一致的SKU生成邏輯
        
        Args:
            product_name: 商品名稱
            color: 顏色
            size: 尺寸
            url: 商品URL
            
        Returns:
            str: 生成的SKU
        """
        try:
            # ✅ 與庫存同步完全一致的邏輯
            
            # 1. 清理輸入
            clean_product_name = re.sub(r'[^\w\s-]', '', product_name)
            clean_color = re.sub(r'[^\w]', '', color)
            clean_size = re.sub(r'[^\w]', '', size)
            
            # 2. 提取商品ID（修正版本，支援goods-sale格式）
            product_id_match = re.search(r'/goods(?:-sale)?[/-](\d+)', url)
            product_id = product_id_match.group(1) if product_id_match else "UNKNOWN"
            
            # 3. 生成唯一字串用於Hash計算
            unique_string = f"{product_id}-{clean_color}-{clean_size}"
            hash_part = hashlib.md5(unique_string.encode("utf-8")).hexdigest()[:4].upper()
            
            # 4. 生成顏色代碼（與庫存同步一致）
            color_code = self.enhanced_color_to_code(color)
            
            # 5. 生成最終SKU
            sku = f"ZO-{hash_part}-{color_code}-{size}"
            
            # 6. 清理SKU
            cleaned_sku = self.clean_sku(sku)
            
            print(f"🔍 SKU生成（折扣同步）:")
            print(f"   商品ID: {product_id}")
            print(f"   原始顏色: {color}")
            print(f"   顏色代碼: {color_code}")
            print(f"   unique_string: {unique_string}")
            print(f"   hash: {hash_part}")
            print(f"   最終SKU: {cleaned_sku}")
            
            return cleaned_sku
            
        except Exception as e:
            print(f"❌ SKU生成失敗: {e}")
            return f"ZO-ERROR-{color[:3] if color else 'UNK'}-{size}"
    
    def enhanced_color_to_code(self, color):
        """✅ 與庫存同步系統完全一致的顏色代碼生成"""
        
        # 與庫存同步完全相同的顏色映射表
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
        """✅ 與庫存同步系統完全一致的SKU清理"""
        if not sku:
            return ""
        # 移除所有空白字符（包括空格、制表符、換行等）
        cleaned_sku = re.sub(r'\s+', '', str(sku))
        return cleaned_sku
    
    def batch_process_discount_sync(self, product_urls):
        """
        批量處理多個商品的折扣同步
        
        Args:
            product_urls: 商品URL列表
            
        Returns:
            list: 所有商品的折扣同步數據
        """
        results = []
        
        for i, url in enumerate(product_urls, 1):
            print(f"🔄 處理商品 {i}/{len(product_urls)}: {url}")
            
            result = self.process_product_for_discount_sync(url)
            result["url"] = url
            results.append(result)
            
            # 添加處理間隔避免過於頻繁請求
            import time
            time.sleep(1)
        
        return results
    
    def get_sync_summary(self, sync_results):
        """
        獲取折扣同步的統計摘要
        
        Args:
            sync_results: 折扣同步結果列表
            
        Returns:
            dict: 統計摘要
        """
        summary = {
            "total_products": len(sync_results),
            "successful_products": 0,
            "failed_products": 0,
            "total_variants": 0,
            "total_discount_amount": 0,
            "average_discount_percentage": 0,
            "errors": []
        }
        
        discount_percentages = []
        
        for result in sync_results:
            if "error" in result:
                summary["failed_products"] += 1
                summary["errors"].append({
                    "url": result.get("url", ""),
                    "error": result["error"]
                })
            else:
                summary["successful_products"] += 1
                summary["total_variants"] += result.get("total_variants", 0)
                
                # 收集折扣百分比
                discount_pct = result.get("discount_percentage", 0)
                if discount_pct > 0:
                    discount_percentages.append(discount_pct)
        
        # 計算平均折扣
        if discount_percentages:
            summary["average_discount_percentage"] = sum(discount_percentages) / len(discount_percentages)
        
        return summary
    
    def extract_main_sku_from_url(self, url):
        """
        從URL快速提取主要SKU（不需要完整解析）
        用於快速SKU匹配
        
        Args:
            url: 商品URL
            
        Returns:
            str: 預估的主要SKU
        """
        try:
            # 提取商品ID
            product_id_match = re.search(r'/goods(?:-sale)?[/-](\d+)', url)
            product_id = product_id_match.group(1) if product_id_match else "UNKNOWN"
            
            # 使用預設值生成SKU（黑色、FREE尺寸）
            default_color = "ブラック"
            default_size = "FREE"
            
            # 生成唯一字串
            unique_string = f"{product_id}-{default_color}-{default_size}"
            hash_part = hashlib.md5(unique_string.encode("utf-8")).hexdigest()[:4].upper()
            
            # 生成顏色代碼
            color_code = self.enhanced_color_to_code(default_color)
            
            # 生成SKU
            sku = f"ZO-{hash_part}-{color_code}-{default_size}"
            
            return self.clean_sku(sku)
            
        except Exception as e:
            print(f"❌ 快速SKU提取失敗: {e}")
            return f"ZO-ERROR-BLK-FREE"


# 便利函數
def process_discount_sync_for_url(url):
    """便利函數：處理單一URL的折扣同步"""
    processor = ZozoDiscountSyncProcessor()
    return processor.process_product_for_discount_sync(url)


def extract_quick_sku(url):
    """便利函數：快速提取SKU"""
    processor = ZozoDiscountSyncProcessor()
    return processor.extract_main_sku_from_url(url)


# 使用範例
if __name__ == "__main__":
    # 創建處理器
    processor = ZozoDiscountSyncProcessor()
    
    # 測試單一商品
    test_url = "https://zozo.jp/shop/mono-mart/goods-sale/73746072/?did=121049876"
    result = processor.process_product_for_discount_sync(test_url)
    
    print("📊 折扣同步結果:")
    print(f"商品名稱: {result.get('product_name', 'N/A')}")
    print(f"折扣百分比: {result.get('discount_percentage', 0)}%")
    print(f"變體數量: {result.get('total_variants', 0)}")
    print(f"主要SKU: {result.get('main_sku', 'N/A')}")
    
    if result.get("variants"):
        print("\n🎯 生成的SKU:")
        for variant in result["variants"][:3]:  # 顯示前3個
            print(f"  {variant['sku']} ({variant['color']}-{variant['size']}) - {variant['discount_percentage']}%折扣")
    
    # 測試快速SKU提取
    quick_sku = processor.extract_main_sku_from_url(test_url)
    print(f"\n⚡ 快速SKU提取: {quick_sku}")
