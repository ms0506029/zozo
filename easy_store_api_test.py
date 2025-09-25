# easy_store_api_test.py
"""
Easy Store API 連接測試工具
完全按照 sync_zozo_discounts_integrated.py 的邏輯進行測試
"""

import requests
import json
import pandas as pd
import os
from config import BASE_API, API_HEADERS

def test_api_with_real_product():
    """使用真實的 product_id 測試 API（模擬原始代碼的使用方式）"""
    print("🔗 測試 Easy Store API 連接...")
    print(f"API URL: {BASE_API}")
    print(f"Headers: {API_HEADERS}")
    
    # 首先嘗試讀取 SKU 映射檔案來獲取真實的 product_id
    sku_mapping_file = 'sku_variant_mapping.xlsx'
    
    if os.path.exists(sku_mapping_file):
        print(f"\n📄 讀取 SKU 映射檔案: {sku_mapping_file}")
        try:
            df = pd.read_excel(sku_mapping_file, engine='openpyxl')
            print(f"✅ 成功載入 {len(df)} 筆映射資料")
            
            # 獲取第一個有效的 product_id
            if not df.empty and 'product_id' in df.columns:
                first_product_id = df['product_id'].iloc[0]
                first_variant_id = df['Variant ID'].iloc[0] if 'Variant ID' in df.columns else None
                first_sku = df['SKU'].iloc[0] if 'SKU' in df.columns else None
                
                print(f"測試資料:")
                print(f"  Product ID: {first_product_id}")
                print(f"  Variant ID: {first_variant_id}")
                print(f"  SKU: {first_sku}")
                
                return test_product_api(first_product_id, first_variant_id)
            else:
                print("❌ SKU 映射檔案格式不正確")
                return False
                
        except Exception as e:
            print(f"❌ 讀取 SKU 映射檔案失敗: {e}")
            return False
    else:
        print(f"❌ 找不到 SKU 映射檔案: {sku_mapping_file}")
        print("請確保檔案存在於當前目錄")
        return False

def test_product_api(product_id, variant_id=None):
    """測試商品 API - 完全按照原始代碼邏輯"""
    print(f"\n📦 測試商品 API (Product ID: {product_id})...")
    
    try:
        # 1. 測試獲取單個商品 - 與原始代碼完全相同
        url = f"{BASE_API}/products/{product_id}.json"
        print(f"🌐 請求 URL: {url}")
        
        response = requests.get(url, headers=API_HEADERS, timeout=10)
        print(f"📊 HTTP 狀態碼: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ 商品 API 連接成功！")
            
            product_data = response.json()
            product = product_data.get("product", {})
            variants = product.get("variants", [])
            
            print(f"📋 商品資訊:")
            print(f"  商品名稱: {product.get('title', 'N/A')}")
            print(f"  商品 ID: {product.get('id', 'N/A')}")
            print(f"  變體數量: {len(variants)}")
            
            # 顯示前 3 個變體
            print(f"📝 變體資訊:")
            for i, variant in enumerate(variants[:3]):
                print(f"  變體 {i+1}:")
                print(f"    ID: {variant.get('id')}")
                print(f"    SKU: {variant.get('sku', 'N/A')}")
                print(f"    價格: {variant.get('price', 0)}")
                print(f"    原價: {variant.get('compare_at_price', 'N/A')}")
            
            # 如果有 variant_id，測試變體更新
            if variant_id and variants:
                # 找到對應的變體
                target_variant = None
                for variant in variants:
                    if variant.get('id') == variant_id:
                        target_variant = variant
                        break
                
                if target_variant:
                    return test_variant_update(product_id, variant_id, target_variant)
                else:
                    print(f"⚠️ 找不到對應的 Variant ID: {variant_id}")
                    # 使用第一個變體測試
                    if variants:
                        first_variant = variants[0]
                        return test_variant_update(product_id, first_variant['id'], first_variant)
            
            return True
            
        elif response.status_code == 401:
            print("❌ 認證失敗 (401)")
            print("請檢查 Access Token 是否正確")
            print("錯誤內容:", response.text)
            return False
            
        elif response.status_code == 404:
            print("❌ 商品不存在 (404)")
            print(f"Product ID {product_id} 可能不存在")
            print("錯誤內容:", response.text)
            return False
            
        else:
            print(f"❌ API 請求失敗: {response.status_code}")
            print("錯誤內容:", response.text)
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 網路連接錯誤: {e}")
        return False
    except Exception as e:
        print(f"❌ 其他錯誤: {e}")
        return False

def test_variant_update(product_id, variant_id, variant_data):
    """測試變體價格更新 - 完全按照原始代碼邏輯"""
    print(f"\n💰 測試變體價格更新...")
    print(f"  Product ID: {product_id}")
    print(f"  Variant ID: {variant_id}")
    
    try:
        # 獲取當前價格
        current_price = int(float(variant_data.get('price', 0)))
        print(f"  當前價格: {current_price}")
        
        if current_price == 0:
            print("⚠️ 當前價格為 0，跳過更新測試")
            return True
        
        # 計算測試價格 (95% 的當前價格，模擬 5% 折扣)
        test_price = int(current_price * 0.95)
        print(f"  測試價格: {test_price}")
        
        # 更新價格 - 與原始代碼完全相同
        url = f"{BASE_API}/products/{product_id}/variants/{variant_id}.json"
        payload = {"variant": {"price": test_price}}
        
        print(f"🌐 更新 URL: {url}")
        print(f"📤 請求資料: {json.dumps(payload)}")
        
        response = requests.put(url, headers=API_HEADERS, json=payload, timeout=10)
        print(f"📊 更新狀態碼: {response.status_code}")
        
        if response.status_code == 200:
            print(f"✅ 價格更新成功: {current_price} → {test_price}")
            
            # 立即還原原價
            restore_payload = {"variant": {"price": current_price}}
            restore_response = requests.put(url, headers=API_HEADERS, json=restore_payload, timeout=10)
            
            if restore_response.status_code == 200:
                print(f"✅ 原價還原成功: {test_price} → {current_price}")
                return True
            else:
                print(f"⚠️ 原價還原失敗 ({restore_response.status_code}): {restore_response.text}")
                return False
        else:
            print(f"❌ 價格更新失敗: {response.status_code}")
            print("錯誤內容:", response.text)
            return False
            
    except Exception as e:
        print(f"❌ 變體更新測試錯誤: {e}")
        return False

def test_sku_mapping_file():
    """測試 SKU 映射檔案的存在和格式"""
    print("📄 檢查 SKU 映射檔案...")
    
    sku_file = 'sku_variant_mapping.xlsx'
    
    if not os.path.exists(sku_file):
        print(f"❌ 找不到檔案: {sku_file}")
        print("請確保檔案存在於當前目錄")
        
        # 列出當前目錄的 Excel 檔案
        excel_files = [f for f in os.listdir('.') if f.endswith(('.xlsx', '.xls'))]
        if excel_files:
            print("📁 當前目錄的 Excel 檔案:")
            for f in excel_files:
                print(f"  - {f}")
        
        return False
    
    try:
        df = pd.read_excel(sku_file, engine='openpyxl')
        print(f"✅ 檔案讀取成功，共 {len(df)} 筆資料")
        
        required_columns = ['SKU', 'product_id', 'Variant ID']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            print(f"❌ 缺少必要欄位: {missing_columns}")
            print(f"現有欄位: {list(df.columns)}")
            return False
        
        print("✅ SKU 映射檔案格式正確")
        return True
        
    except Exception as e:
        print(f"❌ 檔案讀取失敗: {e}")
        return False

def main():
    """主測試流程 - 完全模擬原始代碼的使用方式"""
    print("🧪 Easy Store API 連接測試")
    print("=" * 50)
    print("完全按照 sync_zozo_discounts_integrated.py 的邏輯測試")
    print("=" * 50)
    
    # 1. 檢查 SKU 映射檔案
    if not test_sku_mapping_file():
        print("\n❌ SKU 映射檔案檢查失敗")
        return
    
    # 2. 使用真實的 product_id 測試 API
    if test_api_with_real_product():
        print("\n✅ Easy Store API 測試成功！")
        print("🎉 可以進行下一步：測試完整的同步流程")
    else:
        print("\n❌ Easy Store API 測試失敗")
        print("🔧 請檢查:")
        print("1. config.py 中的 Access Token 是否正確")
        print("2. 商店 URL 是否正確")
        print("3. SKU 映射檔案中的 product_id 是否有效")
    
    print("\n🎉 測試完成！")

if __name__ == "__main__":
    main()
