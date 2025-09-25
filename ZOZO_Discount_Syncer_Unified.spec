# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['sync_zozo_discounts_gui_enhanced.py'],
    pathex=[],
    binaries=[('geckodriver', '.')],
    datas=[('sku_variant_mapping.xlsx', '.'), ('config.py', '.'), ('zozo_html_parser.py', '.'), ('zozo_discount_sync_processor.py', '.'), ('sync_zozo_discounts_integrated.py', '.'), ('zozo_selenium_fetcher.py', '.'), ('zozo_session.py', '.'), ('firefox_profile', 'firefox_profile')],
    hiddenimports=['selenium', 'selenium.webdriver', 'selenium.webdriver.firefox', 'selenium.webdriver.firefox.options', 'selenium.webdriver.common.by', 'selenium.webdriver.support.ui', 'selenium.webdriver.support', 'selenium.common.exceptions', 'beautifulsoup4', 'bs4', 'pandas', 'openpyxl', 'requests', 'hashlib', 're', 'json', 'datetime', 'collections', 'urllib.parse'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ZOZO_Discount_Syncer_Unified',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ZOZO_Discount_Syncer_Unified',
)
app = BUNDLE(
    coll,
    name='ZOZO_Discount_Syncer_Unified.app',
    icon=None,
    bundle_identifier=None,
)
