# export_sku_variant_mapping.py
import os, requests, pandas as pd
from config import BASE_API, API_HEADERS, RESOURCE_DIR, WORK_DIR
import sys
if getattr(sys, "frozen", False):
    exe_dir      = os.path.dirname(sys.executable)
    WORK_DIR     = os.path.normpath(os.path.join(exe_dir, "..", "..", ".."))
    RESOURCE_DIR = os.path.join(exe_dir, "..", "Resources")
else:
    WORK_DIR     = os.path.dirname(os.path.abspath(__file__))
    RESOURCE_DIR = WORK_DIR

def fetch_all_published_products():
    all_p = []
    page = 1
    while True:
        r = requests.get(f"{BASE_API}/products.json?page={page}", headers=API_HEADERS)
        r.raise_for_status()
        prods = r.json().get("products", [])
        if not prods:
            break
        pub = [p for p in prods if p.get("is_published")]
        if not pub:
            break
        all_p += pub
        page += 1
    return all_p

def extract_variant_mapping(products):
    rows = []
    for p in products:
        for v in p.get("variants", []):
            rows.append({
                "Variant ID": v["id"],
                "SKU":       v.get("sku","").strip(),
                "product_id": p["id"],
                "商品名稱":  p.get("title",""),
                # …如需 Option1, Option2 …
            })
    return rows

def export_mapping(output_filename="sku_variant_mapping.xlsx") -> str:
    ps = fetch_all_published_products()
    rows = extract_variant_mapping(ps)
    if not rows:
        raise RuntimeError("無任何已上架商品")
    path = os.path.join(WORK_DIR, output_filename)
    pd.DataFrame(rows).to_excel(path, index=False)
    return path

if __name__ == "__main__":
    print("🔄 產生 SKU ↔ Variant mapping…")
    p = export_mapping()
    print("✅ 輸出至：", p)
