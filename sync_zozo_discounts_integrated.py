# sync_zozo_discounts_integrated.py - 統一版本
"""
ZOZO Town 折扣同步核心模組 - 統一版本
使用與庫存同步系統完全一致的HTML解析邏輯和SKU生成邏輯
"""

import requests
import pandas as pd
import json
import logging
from datetime import datetime
import re
import os
import sys
import hashlib
from config import BASE_API, API_HEADERS

# ✅ 導入統一的ZOZO解析模組
from zozo_selenium_fetcher import fetch_html_from_url_optimized
from zozo_html_parser import ZozoHtmlParser  # 使用統一版本
from zozo_discount_sync_processor import ZozoDiscountSyncProcessor

# 路徑工具
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(__file__)

def resource_path(relative_path):
    """獲取資源的絕對路徑"""
    possible_paths = [
        os.path.abspath(relative_path),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path),
        os.path.join(os.path.dirname(sys.executable), relative_path),
    ]
    
    if hasattr(sys, '_MEIPASS'):
        possible_paths.append(os.path.join(sys._MEIPASS, relative_path))
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return relative_path

# 設定日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')


class ZozoDiscountSyncer:
    def __init__(self, sku_mapping_file='sku_variant_mapping.xlsx'):
        """初始化 ZOZO 折扣同步器"""
        # 讀取 SKU 映射檔案
        sku_mapping_path = resource_path(sku_mapping_file)
        logging.info(f"讀取映射檔案: {sku_mapping_path}")
        
        self.variant_df = pd.read_excel(sku_mapping_path, engine='openpyxl')
        logging.info(f"已載入 {len(self.variant_df)} 筆變體映射資料")
        
        # ✅ 初始化統一的折扣同步處理器
        self.discount_processor = ZozoDiscountSyncProcessor()
        
        # 創建 SKU 映射表 (ZOZO SKU -> Easy Store SKU)
        self.sku_map = {}
        for _, row in self.variant_df.iterrows():
            sku = str(row.get("SKU", "")).strip()
            if sku:
                self.sku_map[sku] = sku  # ZOZO SKU 對應到 Easy Store SKU
        
        logging.info(f"已載入 {len(self.sku_map)} 個 SKU 映射")

    def get_zozo_product_info(self, url):
        """✅ 使用統一解析器獲取 ZOZO Town 商品資訊"""
        try:
            # 使用統一的折扣同步處理器
            discount_data = self.discount_processor.process_product_for_discount_sync(url)
            
            if "error" in discount_data:
                raise ValueError(discount_data["error"])
            
            # 轉換為相容格式
            return {
                'product_name': discount_data.get('product_name', ''),
                'price': discount_data.get('variants', [{}])[0].get('discounted_price', 0),
                'original_price': discount_data.get('variants', [{}])[0].get('original_price', 0),
                'discount_ratio': discount_data.get('discount_ratio', '0%'),
                'discount_pct': discount_data.get('discount_percentage', 0),
                'stocks': [],  # 折扣同步不需要詳細庫存
                'skus': [variant.get('sku', '') for variant in discount_data.get('variants', [])],
                'discount_deadline': discount_data.get('discount_deadline', ''),
                'url': url,
                'main_sku': discount_data.get('main_sku', ''),  # 新增：主要SKU
                'variants': discount_data.get('variants', [])   # 新增：變體列表
            }
            
        except Exception as e:
            logging.error(f"獲取 ZOZO 商品資訊失敗: {url} => {e}")
            raise

    def _extract_discount_percentage(self, discount_str):
        """從折扣字串中提取百分比數字"""
        if not discount_str:
            return 0
        
        match = re.search(r'(\d+)', str(discount_str))
        return int(match.group(1)) if match else 0

    def calculate_easy_discount(self, zozo_discount_pct):
        """計算 Easy Store 折扣百分比 (ZOZO 折扣 - 5%)"""
        if zozo_discount_pct > 5:
            return zozo_discount_pct - 5
        else:
            return max(zozo_discount_pct, 0)

    def find_matching_sku(self, product_info):
        """✅ 智慧 SKU 匹配 - 使用統一生成的SKU"""
        tried_skus = set()
        
        # 優先使用主要SKU
        main_sku = product_info.get('main_sku', '')
        if main_sku:
            tried_skus.add(main_sku)
            if main_sku in self.sku_map:
                easy_sku = self.sku_map[main_sku]
                logging.info(f"主要SKU匹配成功: {main_sku} -> {easy_sku}")
                return main_sku, easy_sku
        
        # 從 ZOZO 生成的 SKU 列表中嘗試匹配
        for zozo_sku in product_info.get('skus', []):
            if zozo_sku in tried_skus:
                continue
                
            tried_skus.add(zozo_sku)
            
            if zozo_sku in self.sku_map:
                easy_sku = self.sku_map[zozo_sku]
                logging.info(f"找到 SKU 匹配: {zozo_sku} -> {easy_sku}")
                return zozo_sku, easy_sku
        
        # 如果直接匹配失敗，記錄嘗試的 SKU
        if tried_skus:
            logging.warning(f"嘗試了 {len(tried_skus)} 個 ZOZO SKU 但未找到匹配:")
            for i, sku in enumerate(list(tried_skus)[:5]):  # 只顯示前 5 個
                logging.warning(f"  {i+1}. {sku}")
        
        # 列出一些現有的 SKU 作為參考
        existing_skus = list(self.sku_map.keys())[:10]
        logging.warning("參考現有 SKU 格式:")
        for i, sku in enumerate(existing_skus):
            logging.warning(f"  {i+1}. {sku}")
        
        raise ValueError("找不到匹配的 Easy Store SKU")

    def get_variant_info(self, easy_sku):
        """獲取變體資訊"""
        easy_sku_str = str(easy_sku).strip()
        
        # 從本地映射表查找
        row = self.variant_df[
            self.variant_df['SKU'].astype(str).str.strip() == easy_sku_str
        ]
        
        if not row.empty:
            return {
                "product_id": int(row['product_id'].iat[0]),
                "variant_id": int(row['Variant ID'].iat[0]),
                "price": row.get('price', [0]).iat[0] if 'price' in row else 0,
                "compare_at_price": row.get('compare_at_price', [0]).iat[0] if 'compare_at_price' in row else 0
            }
        
        raise ValueError(f"找不到對應的 Variant ID: {easy_sku_str}")

    def get_all_product_variants(self, product_id):
        """獲取指定商品的所有變體"""
        try:
            url = f"{BASE_API}/products/{product_id}.json"
            resp = requests.get(url, headers=API_HEADERS)
            resp.raise_for_status()
            
            product_data = resp.json().get("product", {})
            variants = product_data.get("variants", [])
            
            # 確保價格字段是數值類型
            for variant in variants:
                try:
                    if "price" in variant:
                        variant["price"] = int(float(variant["price"])) if variant["price"] else 0
                    if "compare_at_price" in variant:
                        cap = variant["compare_at_price"]
                        variant["compare_at_price"] = int(float(cap)) if cap and str(cap).strip() else None
                except (TypeError, ValueError):
                    logging.warning(f"轉換變體價格類型失敗: {variant.get('id')}")
            
            logging.info(f"獲取到商品 {product_id} 的 {len(variants)} 個變體")
            return variants
            
        except Exception as e:
            logging.error(f"獲取商品變體失敗: {product_id} => {e}")
            raise

    def update_variant_price(self, product_id, variant_id, new_price):
        """更新 Easy Store 商品變體的價格"""
        try:
            url = f"{BASE_API}/products/{product_id}/variants/{variant_id}.json"
            payload = {"variant": {"price": new_price}}
            resp = requests.put(url, headers=API_HEADERS, json=payload)
            resp.raise_for_status()
            logging.info(f"已更新變體 {variant_id} 價格: {new_price}")
            return resp.json()
            
        except Exception as e:
            logging.error(f"更新變體價格失敗: {variant_id} => {e}")
            raise

    def sync_discount(self, url, apply_additional_discount=False):
        """✅ 同步單一 URL 的折扣到 Easy Store 所有變體"""
        try:
            # 1. 獲取 ZOZO 商品資訊（使用統一解析器）
            logging.info(f"開始處理 ZOZO 商品: {url}")
            product_info = self.get_zozo_product_info(url)
            
            # 2. 找到匹配的 SKU
            zozo_sku, easy_sku = self.find_matching_sku(product_info)
            logging.info(f"SKU 匹配成功: {zozo_sku} -> {easy_sku}")
            
            # 3. 計算 Easy Store 折扣
            zozo_discount = product_info['discount_pct']
            easy_discount = self.calculate_easy_discount(zozo_discount)
            logging.info(f"折扣計算: ZOZO {zozo_discount}% -> Easy {easy_discount}%")
            
            # 4. 獲取變體資訊
            variant_info = self.get_variant_info(easy_sku)
            product_id = variant_info["product_id"]
            reference_variant_id = variant_info["variant_id"]
            
            # 5. 獲取商品的所有變體
            all_variants = self.get_all_product_variants(product_id)
            logging.info(f"準備更新 {len(all_variants)} 個變體的價格")
            
            # 6. 對所有變體套用相同折扣
            updated_variants = []
            final_price = 0
            
            for variant in all_variants:
                variant_id = variant["id"]
                
                # 取得原價 (優先使用 compare_at_price)
                try:
                    price = int(float(variant.get("price", 0)))
                    compare_price = int(float(variant.get("compare_at_price", price)))
                except (TypeError, ValueError):
                    price = 0
                    compare_price = price
                
                # 計算折扣後價格
                discounted_price = round(compare_price * (100 - easy_discount) / 100)
                
                # 高價商品額外折扣
                if discounted_price > 5000 and apply_additional_discount:
                    final_price = round(discounted_price * 0.85)
                    need_additional_discount = True
                else:
                    final_price = discounted_price
                    need_additional_discount = False
                
                # 更新價格
                self.update_variant_price(product_id, variant_id, final_price)
                
                # 記錄更新結果
                updated_variants.append({
                    "variant_id": variant_id,
                    "sku": variant.get("sku", ""),
                    "original_price": compare_price,
                    "discounted_price": discounted_price,
                    "final_price": final_price,
                    "additional_discount": need_additional_discount
                })
            
            logging.info(f"成功更新 {len(updated_variants)} 個變體")
            
            # 7. 返回結果
            return {
                'success': True,
                'zozo_sku': zozo_sku,
                'easy_sku': easy_sku,
                'url': url,
                'zozo_discount': zozo_discount,
                'easy_discount': easy_discount,
                'original_price': product_info['original_price'],
                'final_price': final_price,
                'high_price': any(v['additional_discount'] for v in updated_variants),
                'additional_discount_applied': apply_additional_discount and any(v['additional_discount'] for v in updated_variants),
                'product_id': product_id,
                'variant_id': reference_variant_id,
                'updated_variants_count': len(updated_variants),
                'updated_variants': updated_variants,
                'discount_deadline': product_info.get('discount_deadline', '')
            }
            
        except Exception as e:
            logging.error(f"同步折扣失敗: {url} => {e}")
            return {
                'success': False,
                'url': url,
                'error': str(e)
            }

    def restore_original_prices(self, url):
        """還原商品到原價"""
        try:
            # 1. 獲取 ZOZO 商品資訊 (主要為了找 SKU)
            product_info = self.get_zozo_product_info(url)
            
            # 2. 找到匹配的 SKU
            zozo_sku, easy_sku = self.find_matching_sku(product_info)
            
            # 3. 獲取變體資訊
            variant_info = self.get_variant_info(easy_sku)
            product_id = variant_info["product_id"]
            
            # 4. 獲取所有變體
            all_variants = self.get_all_product_variants(product_id)
            
            # 5. 還原所有變體的原價
            restored_variants = []
            
            for variant in all_variants:
                variant_id = variant["id"]
                
                # 取得原價
                try:
                    compare_price = int(float(variant.get("compare_at_price", 0)))
                    if not compare_price:
                        compare_price = int(float(variant.get("price", 0)))
                except (TypeError, ValueError):
                    compare_price = 0
                
                if compare_price > 0:
                    # 還原為原價
                    self.update_variant_price(product_id, variant_id, compare_price)
                    
                    restored_variants.append({
                        "variant_id": variant_id,
                        "sku": variant.get("sku", ""),
                        "restored_price": compare_price
                    })
            
            logging.info(f"成功還原 {len(restored_variants)} 個變體的原價")
            
            return {
                'success': True,
                'zozo_sku': zozo_sku,
                'easy_sku': easy_sku,
                'url': url,
                'product_id': product_id,
                'restored_variants_count': len(restored_variants),
                'restored_variants': restored_variants
            }
            
        except Exception as e:
            logging.error(f"還原原價失敗: {url} => {e}")
            return {
                'success': False,
                'url': url,
                'error': str(e)
            }


# 便利函數供外部使用
def sync_zozo_discount(url, apply_additional_discount=False):
    """便利函數：同步單一 ZOZO 商品折扣"""
    syncer = ZozoDiscountSyncer()
    return syncer.sync_discount(url, apply_additional_discount)

def restore_zozo_prices(url):
    """便利函數：還原單一 ZOZO 商品原價"""
    syncer = ZozoDiscountSyncer()
    return syncer.restore_original_prices(url)


if __name__ == "__main__":
    # 測試代碼
    test_url = "https://zozo.jp/shop/mono-mart/goods/93988386/?did=151898814&rid=1006"
    
    syncer = ZozoDiscountSyncer()
    
    print("✅ 測試折扣同步...")
    result = syncer.sync_discount(test_url, apply_additional_discount=True)
    
    if result['success']:
        print(f"同步成功!")
        print(f"ZOZO SKU: {result['zozo_sku']}")
        print(f"Easy SKU: {result['easy_sku']}")
        print(f"折扣: {result['zozo_discount']}% -> {result['easy_discount']}%")
        print(f"更新了 {result['updated_variants_count']} 個變體")
    else:
        print(f"同步失敗: {result['error']}")
    
    print("\n📊 統一SKU生成邏輯測試完成！")
