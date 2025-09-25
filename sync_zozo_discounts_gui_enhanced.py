# sync_zozo_discounts_gui_enhanced.py
"""
ZOZO Town 折扣同步 GUI 應用程式 - 增強版
新增功能：URL 驗證、自動重試、即時預覽、排程功能等
"""

import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk, filedialog, simpledialog
import threading
import pandas as pd
from datetime import datetime, timedelta
import os
import sys
import json
import re
import time
from urllib.parse import urlparse
# 導入 ZOZO 會員登入模組
from zozo_session import setup_zozo_session, cleanup_zozo_session, get_zozo_product_info

# 導入核心同步模組
from sync_zozo_discounts_integrated import ZozoDiscountSyncer


class EnhancedZozoDiscountSyncApp:
    def __init__(self, root):
        self.root = root
        root.title("ZOZO Town 折扣同步器 - 增強版 v2.0")
        root.geometry("900x750")
        root.minsize(800, 600)
        
        # 設定檔案路徑
        self.config_file = "zozo_sync_config.json"
        self.urls_file_path = "zozo_tracked_urls.txt"
        self.schedule_file = "zozo_sync_schedule.json"
        
        # 初始化屬性
        self.log_box = None
        self.sync_results = []
        self.is_syncing = False
        self.schedule_thread = None
        self.stop_schedule = False
        # ZOZO 會員登入狀態
        self.zozo_logged_in = False
        
        
        # 讀取設定檔
        self.load_config()
        
        # 建立 GUI
        self.create_enhanced_gui()
        
        # 初始化同步器
        try:
            self.syncer = ZozoDiscountSyncer()
            self.log("✅ ZOZO 同步器初始化成功")
        except Exception as e:
            self.log(f"❌ 同步器初始化失敗: {e}")
            messagebox.showerror("初始化錯誤", f"同步器初始化失敗:\n{e}")
        
        # 載入追蹤 URL
        self.load_tracked_urls()
        
        # 載入排程設定
        self.load_schedule_config()
        
        # 關閉視窗處理
        root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def load_config(self):
        """載入設定檔"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            else:
                self.config = {}
        except Exception as e:
            print(f"載入設定檔失敗: {e}")
            self.config = {}
        
        # 預設設定
        defaults = {
            'high_price_discount': False,
            'auto_save_urls': True,
            'auto_retry_failed': True,
            'retry_count': 3,
            'retry_delay': 5,
            'validate_urls': True,
            'backup_before_sync': True,
            'log_level': 'INFO'
        }
        
        for key, value in defaults.items():
            if key not in self.config:
                self.config[key] = value

    def save_config(self):
        """儲存設定檔"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            self.log(f"❌ 儲存設定檔失敗: {e}")

    def create_enhanced_gui(self):
        """創建增強版 GUI"""
        # 建立筆記本控件 (分頁式介面)
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        # 主要操作頁面
        self.main_frame = ttk.Frame(notebook)
        notebook.add(self.main_frame, text="📋 主要操作")
        self.create_main_tab()
        
        # 進階設定頁面
        self.settings_frame = ttk.Frame(notebook)
        notebook.add(self.settings_frame, text="⚙️ 進階設定")
        self.create_settings_tab()
        
        # 排程管理頁面
        self.schedule_frame = ttk.Frame(notebook)
        notebook.add(self.schedule_frame, text="⏰ 排程管理")
        self.create_schedule_tab()
        
        # 統計報表頁面
        self.stats_frame = ttk.Frame(notebook)
        notebook.add(self.stats_frame, text="📊 統計報表")
        self.create_stats_tab()

    def create_main_tab(self):
        """創建主要操作頁面"""
        # 標題區域
        title_frame = ttk.Frame(self.main_frame)
        title_frame.pack(fill='x', padx=10, pady=5)
        
        title_label = ttk.Label(
            title_frame,
            text="ZOZO Town → Easy Store 折扣同步器",
            font=("Arial", 16, "bold")
        )
        title_label.pack()
        
        # 狀態指示器
        status_frame = ttk.Frame(title_frame)
        status_frame.pack(fill='x', pady=5)
        
        self.status_var = tk.StringVar(value="🟢 就緒")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var, font=("Arial", 10))
        self.status_label.pack(side='left')
        
        # 即時時間顯示
        self.time_var = tk.StringVar()
        self.time_label = ttk.Label(status_frame, textvariable=self.time_var, font=("Arial", 9))
        self.time_label.pack(side='right')
        self.update_time()
        
        # URL 管理區域 (增強版)
        url_frame = ttk.LabelFrame(self.main_frame, text="🔗 ZOZO 商品 URL 管理")
        url_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # URL 工具列
        toolbar_frame = ttk.Frame(url_frame)
        toolbar_frame.pack(fill='x', side='top', padx=5, pady=5)
        
        # 左側按鈕
        left_buttons = ttk.Frame(toolbar_frame)
        left_buttons.pack(side='left')
        
        ttk.Button(left_buttons, text="📂 載入檔案", command=self.load_url_file).pack(side='left', padx=2)
        ttk.Button(left_buttons, text="💾 儲存檔案", command=self.save_url_file).pack(side='left', padx=2)
        ttk.Button(left_buttons, text="➕ 新增", command=self.add_url).pack(side='left', padx=2)
        ttk.Button(left_buttons, text="📝 批量新增", command=self.batch_add_urls).pack(side='left', padx=2)
        
        # 右側按鈕
        right_buttons = ttk.Frame(toolbar_frame)
        right_buttons.pack(side='right')
        
        ttk.Button(right_buttons, text="✅ 驗證 URL", command=self.validate_urls).pack(side='left', padx=2)
        ttk.Button(right_buttons, text="🗑️ 移除所選", command=self.remove_selected_urls).pack(side='left', padx=2)
        ttk.Button(right_buttons, text="🧹 清空全部", command=self.clear_all_urls).pack(side='left', padx=2)
        
        # URL 列表區域
        list_container = ttk.Frame(url_frame)
        list_container.pack(fill='both', expand=True, padx=5, pady=5)
        
        # 創建 Treeview 取代 Listbox（支援多欄顯示）
        columns = ('url', 'status', 'last_sync', 'discount')
        self.url_tree = ttk.Treeview(list_container, columns=columns, show='tree headings', height=8)
        
        # 設定欄位
        self.url_tree.heading('#0', text='#', anchor='w')
        self.url_tree.heading('url', text='URL', anchor='w')
        self.url_tree.heading('status', text='狀態', anchor='center')
        self.url_tree.heading('last_sync', text='最後同步', anchor='center')
        self.url_tree.heading('discount', text='當前折扣', anchor='center')
        
        # 設定欄寬
        self.url_tree.column('#0', width=40, minwidth=40)
        self.url_tree.column('url', width=400, minwidth=200)
        self.url_tree.column('status', width=80, minwidth=60)
        self.url_tree.column('last_sync', width=120, minwidth=100)
        self.url_tree.column('discount', width=80, minwidth=60)
        
        self.url_tree.pack(side='left', fill='both', expand=True)
        
        # 滾動條
        tree_scrollbar = ttk.Scrollbar(list_container, orient='vertical', command=self.url_tree.yview)
        tree_scrollbar.pack(side='right', fill='y')
        self.url_tree.configure(yscrollcommand=tree_scrollbar.set)
        
        # URL 統計
        stats_frame = ttk.Frame(url_frame)
        stats_frame.pack(fill='x', padx=5, pady=2)
        
        self.url_count_var = tk.StringVar(value="URL 數量: 0")
        ttk.Label(stats_frame, textvariable=self.url_count_var).pack(side='left')
        
        self.valid_count_var = tk.StringVar(value="有效: 0")
        ttk.Label(stats_frame, textvariable=self.valid_count_var, foreground='green').pack(side='left', padx=10)
        
        self.invalid_count_var = tk.StringVar(value="無效: 0")
        ttk.Label(stats_frame, textvariable=self.invalid_count_var, foreground='red').pack(side='left', padx=10)
        
        # 快速操作區域
        quick_frame = ttk.LabelFrame(self.main_frame, text="🚀 快速操作")
        quick_frame.pack(fill='x', padx=10, pady=5)
        
        # 折扣設定
        discount_settings = ttk.Frame(quick_frame)
        discount_settings.pack(fill='x', padx=10, pady=5)
        
        # 高價商品折扣
        self.high_price_var = tk.BooleanVar(value=self.config.get('high_price_discount', False))
        ttk.Checkbutton(
            discount_settings,
            text="💰 對折後價格 > 5000 的商品額外折 15%",
            variable=self.high_price_var,
            command=self.save_high_price_setting
        ).pack(side='left')
        
        
        # ZOZO 會員登入區域
        login_frame = ttk.LabelFrame(quick_frame, text="🔐 ZOZO 會員登入")
        login_frame.pack(fill='x', padx=10, pady=5)

        # 登入狀態顯示
        self.zozo_login_status_var = tk.StringVar(value="🔴 尚未登入")
        self.zozo_login_status_label = ttk.Label(
            login_frame,
            textvariable=self.zozo_login_status_var,
            font=("Arial", 10)
        )
        self.zozo_login_status_label.pack(pady=5)

        # 登入按鈕
        ttk.Button(
            login_frame,
            text="🔑 ZOZO Town 會員登入",
            command=self.login_zozo_town
        ).pack(pady=5)
        
        # 自動重試
        self.auto_retry_var = tk.BooleanVar(value=self.config.get('auto_retry_failed', True))
        ttk.Checkbutton(
            discount_settings,
            text="🔄 自動重試失敗的項目",
            variable=self.auto_retry_var,
            command=self.save_auto_retry_setting
        ).pack(side='left', padx=20)
        
        # 主要操作按鈕
        action_frame = ttk.Frame(quick_frame)
        action_frame.pack(fill='x', padx=10, pady=10)
        
        # 左側按鈕
        left_actions = ttk.Frame(action_frame)
        left_actions.pack(side='left')
        
        self.sync_btn = ttk.Button(
            left_actions,
            text="🔄 開始同步折扣",
            command=self.start_sync,
            style='Accent.TButton'
        )
        self.sync_btn.pack(side='left', padx=5)
        
        self.restore_btn = ttk.Button(
            left_actions,
            text="🔙 還原原價",
            command=self.restore_original_prices
        )
        self.restore_btn.pack(side='left', padx=5)
        
        self.test_btn = ttk.Button(
            left_actions,
            text="🧪 測試單一商品",
            command=self.test_single_product
        )
        self.test_btn.pack(side='left', padx=5)
        
        # 右側按鈕
        right_actions = ttk.Frame(action_frame)
        right_actions.pack(side='right')
        
        ttk.Button(
            right_actions,
            text="📊 匯出結果",
            command=self.export_results
        ).pack(side='left', padx=5)
        
        ttk.Button(
            right_actions,
            text="⏹️ 停止操作",
            command=self.stop_operation,
            state='disabled'
        ).pack(side='left', padx=5)
        
        # 進度顯示
        progress_frame = ttk.Frame(quick_frame)
        progress_frame.pack(fill='x', padx=10, pady=5)
        
        self.progress_var = tk.DoubleVar()
        self.progress = ttk.Progressbar(
            progress_frame,
            orient='horizontal',
            mode='determinate',
            variable=self.progress_var
        )
        self.progress.pack(fill='x', side='top')
        
        self.progress_text_var = tk.StringVar(value="")
        ttk.Label(progress_frame, textvariable=self.progress_text_var, font=("Arial", 9)).pack(pady=2)
        
        # 日誌區域 (增強版)
        log_frame = ttk.LabelFrame(self.main_frame, text="📝 執行日誌")
        log_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # 日誌工具列
        log_toolbar = ttk.Frame(log_frame)
        log_toolbar.pack(fill='x', padx=5, pady=2)
        
        # 日誌等級過濾
        ttk.Label(log_toolbar, text="等級:").pack(side='left')
        
        self.log_level_var = tk.StringVar(value="全部")
        log_level_combo = ttk.Combobox(
            log_toolbar,
            textvariable=self.log_level_var,
            values=["全部", "INFO", "WARNING", "ERROR"],
            state="readonly",
            width=8
        )
        log_level_combo.pack(side='left', padx=5)
        log_level_combo.bind("<<ComboboxSelected>>", self.filter_logs)
        
        # 日誌操作按鈕
        ttk.Button(log_toolbar, text="🧹 清空", command=self.clear_log).pack(side='right', padx=2)
        ttk.Button(log_toolbar, text="💾 儲存", command=self.save_log).pack(side='right', padx=2)
        ttk.Button(log_toolbar, text="🔍 搜尋", command=self.search_log).pack(side='right', padx=2)
        
        # 日誌顯示區域
        log_container = ttk.Frame(log_frame)
        log_container.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.log_box = scrolledtext.ScrolledText(
            log_container,
            height=10,
            font=("Consolas", 9),
            wrap=tk.WORD
        )
        self.log_box.pack(fill='both', expand=True)
        
        # 設定日誌顏色標籤
        self.log_box.tag_configure("INFO", foreground="black")
        self.log_box.tag_configure("SUCCESS", foreground="green", font=("Consolas", 9, "bold"))
        self.log_box.tag_configure("WARNING", foreground="orange")
        self.log_box.tag_configure("ERROR", foreground="red", font=("Consolas", 9, "bold"))
        self.log_box.tag_configure("DEBUG", foreground="gray")

    def create_settings_tab(self):
        """創建進階設定頁面"""
        # 捲動框架
        canvas = tk.Canvas(self.settings_frame)
        scrollbar = ttk.Scrollbar(self.settings_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 一般設定
        general_frame = ttk.LabelFrame(scrollable_frame, text="🔧 一般設定")
        general_frame.pack(fill='x', padx=10, pady=10)
        
        # 自動儲存 URL
        self.auto_save_var = tk.BooleanVar(value=self.config.get('auto_save_urls', True))
        ttk.Checkbutton(
            general_frame,
            text="自動儲存 URL 變更",
            variable=self.auto_save_var,
            command=self.save_auto_save_setting
        ).pack(anchor='w', padx=10, pady=5)
        
        # URL 驗證
        self.validate_urls_var = tk.BooleanVar(value=self.config.get('validate_urls', True))
        ttk.Checkbutton(
            general_frame,
            text="新增 URL 時自動驗證",
            variable=self.validate_urls_var,
            command=self.save_validate_urls_setting
        ).pack(anchor='w', padx=10, pady=5)
        
        # 同步前備份
        self.backup_var = tk.BooleanVar(value=self.config.get('backup_before_sync', True))
        ttk.Checkbutton(
            general_frame,
            text="同步前自動備份設定",
            variable=self.backup_var,
            command=self.save_backup_setting
        ).pack(anchor='w', padx=10, pady=5)
        
        # 重試設定
        retry_frame = ttk.LabelFrame(scrollable_frame, text="🔄 重試設定")
        retry_frame.pack(fill='x', padx=10, pady=10)
        
        # 重試次數
        retry_count_frame = ttk.Frame(retry_frame)
        retry_count_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(retry_count_frame, text="重試次數:").pack(side='left')
        self.retry_count_var = tk.IntVar(value=self.config.get('retry_count', 3))
        retry_spin = tk.Spinbox(
            retry_count_frame,
            from_=1,
            to=10,
            textvariable=self.retry_count_var,
            width=5,
            command=self.save_retry_settings
        )
        retry_spin.pack(side='left', padx=10)
        
        # 重試延遲
        retry_delay_frame = ttk.Frame(retry_frame)
        retry_delay_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(retry_delay_frame, text="重試延遲(秒):").pack(side='left')
        self.retry_delay_var = tk.IntVar(value=self.config.get('retry_delay', 5))
        delay_spin = tk.Spinbox(
            retry_delay_frame,
            from_=1,
            to=60,
            textvariable=self.retry_delay_var,
            width=5,
            command=self.save_retry_settings
        )
        delay_spin.pack(side='left', padx=10)
        
        # 折扣策略設定
        strategy_frame = ttk.LabelFrame(scrollable_frame, text="💰 折扣策略")
        strategy_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(strategy_frame, text="基本規則: ZOZO 折扣 - 5% = Easy Store 折扣").pack(anchor='w', padx=10, pady=5)
        
        # 高價商品設定
        high_price_frame = ttk.Frame(strategy_frame)
        high_price_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(high_price_frame, text="高價商品門檻:").pack(side='left')
        self.high_price_threshold_var = tk.IntVar(value=self.config.get('high_price_threshold', 5000))
        threshold_spin = tk.Spinbox(
            high_price_frame,
            from_=1000,
            to=20000,
            increment=1000,
            textvariable=self.high_price_threshold_var,
            width=8,
            command=self.save_threshold_setting
        )
        threshold_spin.pack(side='left', padx=10)
        
        ttk.Label(high_price_frame, text="額外折扣:").pack(side='left', padx=20)
        self.additional_discount_var = tk.IntVar(value=self.config.get('additional_discount', 15))
        discount_spin = tk.Spinbox(
            high_price_frame,
            from_=5,
            to=50,
            increment=5,
            textvariable=self.additional_discount_var,
            width=5,
            command=self.save_additional_discount_setting
        )
        discount_spin.pack(side='left', padx=10)
        ttk.Label(high_price_frame, text="%").pack(side='left')
        
        # 包裝滾動框架
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def create_schedule_tab(self):
        """創建排程管理頁面"""
        # 排程狀態
        status_frame = ttk.LabelFrame(self.schedule_frame, text="📊 排程狀態")
        status_frame.pack(fill='x', padx=10, pady=10)
        
        self.schedule_status_var = tk.StringVar(value="⏹️ 未啟用")
        ttk.Label(status_frame, textvariable=self.schedule_status_var, font=("Arial", 12)).pack(pady=10)
        
        # 排程設定
        schedule_config_frame = ttk.LabelFrame(self.schedule_frame, text="⚙️ 排程設定")
        schedule_config_frame.pack(fill='x', padx=10, pady=10)
        
        # 啟用排程
        self.enable_schedule_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            schedule_config_frame,
            text="啟用自動排程",
            variable=self.enable_schedule_var,
            command=self.toggle_schedule
        ).pack(anchor='w', padx=10, pady=5)
        
        # 執行間隔
        interval_frame = ttk.Frame(schedule_config_frame)
        interval_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(interval_frame, text="執行間隔:").pack(side='left')
        self.schedule_interval_var = tk.IntVar(value=60)
        interval_spin = tk.Spinbox(
            interval_frame,
            from_=5,
            to=1440,
            textvariable=self.schedule_interval_var,
            width=8
        )
        interval_spin.pack(side='left', padx=10)
        ttk.Label(interval_frame, text="分鐘").pack(side='left')
        
        # 排程控制按鈕
        control_frame = ttk.Frame(schedule_config_frame)
        control_frame.pack(fill='x', padx=10, pady=10)
        
        self.start_schedule_btn = ttk.Button(
            control_frame,
            text="▶️ 啟動排程",
            command=self.start_schedule
        )
        self.start_schedule_btn.pack(side='left', padx=5)
        
        self.stop_schedule_btn = ttk.Button(
            control_frame,
            text="⏹️ 停止排程",
            command=self.stop_schedule_func,
            state='disabled'
        )
        self.stop_schedule_btn.pack(side='left', padx=5)
        
        # 下次執行時間
        self.next_run_var = tk.StringVar(value="")
        ttk.Label(schedule_config_frame, textvariable=self.next_run_var).pack(pady=5)
        
        # 排程歷史
        history_frame = ttk.LabelFrame(self.schedule_frame, text="📜 執行歷史")
        history_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # 歷史記錄列表
        history_columns = ('time', 'status', 'processed', 'success', 'failed')
        self.history_tree = ttk.Treeview(history_frame, columns=history_columns, show='headings', height=8)
        
        self.history_tree.heading('time', text='執行時間')
        self.history_tree.heading('status', text='狀態')
        self.history_tree.heading('processed', text='處理數')
        self.history_tree.heading('success', text='成功數')
        self.history_tree.heading('failed', text='失敗數')
        
        self.history_tree.pack(fill='both', expand=True, padx=5, pady=5)

    def create_stats_tab(self):
        """創建統計報表頁面"""
        # 總體統計
        overview_frame = ttk.LabelFrame(self.stats_frame, text="📈 總體統計")
        overview_frame.pack(fill='x', padx=10, pady=10)
        
        stats_grid = ttk.Frame(overview_frame)
        stats_grid.pack(padx=10, pady=10)
        
        # 統計項目
        self.stats_labels = {}
        stats_items = [
            ('total_syncs', '總同步次數'),
            ('successful_syncs', '成功同步'),
            ('failed_syncs', '失敗同步'),
            ('total_savings', '總節省金額'),
            ('avg_discount', '平均折扣'),
            ('last_sync', '最後同步')
        ]
        
        for i, (key, label) in enumerate(stats_items):
            row = i // 3
            col = (i % 3) * 2
            
            ttk.Label(stats_grid, text=f"{label}:", font=("Arial", 10)).grid(
                row=row, column=col, sticky='w', padx=5, pady=2
            )
            
            value_label = ttk.Label(stats_grid, text="0", font=("Arial", 10, "bold"))
            value_label.grid(row=row, column=col+1, sticky='w', padx=10, pady=2)
            self.stats_labels[key] = value_label
        
        # 更新統計按鈕
        ttk.Button(
            overview_frame,
            text="🔄 更新統計",
            command=self.update_stats
        ).pack(pady=10)

    def batch_add_urls(self):
        """批量新增 URL"""
        def add_urls():
            urls_text = text_widget.get(1.0, tk.END).strip()
            if not urls_text:
                messagebox.showwarning("提示", "請輸入 URL")
                return
            
            urls = [url.strip() for url in urls_text.split('\n') if url.strip()]
            invalid_urls = []
            added_count = 0
            
            for url in urls:
                if not url.startswith(('http://', 'https://')):
                    url = 'https://' + url
                
                if "zozo.jp" in url.lower():
                    self.add_url_to_tree(url)
                    added_count += 1
                else:
                    invalid_urls.append(url)
            
            dialog.destroy()
            
            if added_count > 0:
                self.update_url_count()
                self.save_tracked_urls()
                self.log(f"✅ 批量新增了 {added_count} 個 URL")
            
            if invalid_urls:
                messagebox.showwarning(
                    "部分 URL 無效",
                    f"以下 {len(invalid_urls)} 個 URL 格式不正確:\n" + "\n".join(invalid_urls[:5])
                )
        
        dialog = tk.Toplevel(self.root)
        dialog.title("批量新增 ZOZO URL")
        dialog.geometry("700x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="每行輸入一個 ZOZO Town 商品 URL:").pack(padx=10, pady=5)
        
        text_widget = scrolledtext.ScrolledText(dialog, height=15)
        text_widget.pack(fill='both', expand=True, padx=10, pady=5)
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(padx=10, pady=10)
        
        ttk.Button(btn_frame, text="新增", command=add_urls).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side='left', padx=5)

    def add_url_to_tree(self, url, status="待驗證", last_sync="", discount=""):
        """新增 URL 到樹狀列表"""
        item_id = self.url_tree.insert('', 'end', values=(url, status, last_sync, discount))
        return item_id

    def validate_urls(self):
        """驗證所有 URL"""
        items = self.url_tree.get_children()
        if not items:
            messagebox.showinfo("提示", "沒有 URL 需要驗證")
            return
        
        self.log("🔍 開始驗證 URL...")
        
        threading.Thread(target=self.validate_urls_worker, args=(items,), daemon=True).start()

    def validate_urls_worker(self, items):
        """URL 驗證工作線程"""
        valid_count = 0
        invalid_count = 0
        
        for item in items:
            try:
                values = self.url_tree.item(item, 'values')
                url = values[0]
                
                # 簡單的 URL 格式驗證
                if self.is_valid_zozo_url(url):
                    self.root.after(0, lambda i=item: self.url_tree.set(i, 'status', '✅ 有效'))
                    valid_count += 1
                else:
                    self.root.after(0, lambda i=item: self.url_tree.set(i, 'status', '❌ 無效'))
                    invalid_count += 1
                
                time.sleep(0.1)  # 避免過於頻繁的更新
                
            except Exception as e:
                self.root.after(0, lambda i=item: self.url_tree.set(i, 'status', '❓ 錯誤'))
                invalid_count += 1
        
        self.root.after(0, lambda: self.log(f"✅ URL 驗證完成：有效 {valid_count}，無效 {invalid_count}"))
        self.root.after(0, self.update_url_count)

    def is_valid_zozo_url(self, url):
        """驗證是否為有效的 ZOZO URL"""
        try:
            parsed = urlparse(url)
            return (
                parsed.scheme in ['http', 'https'] and
                'zozo.jp' in parsed.netloc.lower() and
                '/goods/' in parsed.path
            )
        except:
            return False

    def update_time(self):
        """更新時間顯示"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_var.set(current_time)
        self.root.after(1000, self.update_time)

    def save_high_price_setting(self):
        """儲存高價商品折扣設定"""
        self.config['high_price_discount'] = self.high_price_var.get()
        self.save_config()

    def save_auto_retry_setting(self):
        """儲存自動重試設定"""
        self.config['auto_retry_failed'] = self.auto_retry_var.get()
        self.save_config()

    def save_auto_save_setting(self):
        """儲存自動儲存設定"""
        self.config['auto_save_urls'] = self.auto_save_var.get()
        self.save_config()

    def save_validate_urls_setting(self):
        """儲存 URL 驗證設定"""
        self.config['validate_urls'] = self.validate_urls_var.get()
        self.save_config()

    def save_backup_setting(self):
        """儲存備份設定"""
        self.config['backup_before_sync'] = self.backup_var.get()
        self.save_config()

    def save_retry_settings(self):
        """儲存重試設定"""
        self.config['retry_count'] = self.retry_count_var.get()
        self.config['retry_delay'] = self.retry_delay_var.get()
        self.save_config()

    def save_threshold_setting(self):
        """儲存高價門檻設定"""
        self.config['high_price_threshold'] = self.high_price_threshold_var.get()
        self.save_config()

    def save_additional_discount_setting(self):
        """儲存額外折扣設定"""
        self.config['additional_discount'] = self.additional_discount_var.get()
        self.save_config()

    def load_tracked_urls(self):
        """載入追蹤 URL"""
        try:
            if os.path.exists(self.urls_file_path):
                with open(self.urls_file_path, 'r', encoding='utf-8') as f:
                    urls = [line.strip() for line in f if line.strip()]
                
                # 清空現有項目
                for item in self.url_tree.get_children():
                    self.url_tree.delete(item)
                
                # 新增 URL
                for url in urls:
                    self.add_url_to_tree(url)
                
                self.update_url_count()
                self.log(f"📂 已載入 {len(urls)} 個追蹤 URL")
            else:
                self.log("📝 未找到追蹤 URL 檔案")
        except Exception as e:
            self.log(f"❌ 載入 URL 失敗: {e}")

    def save_tracked_urls(self):
        """儲存追蹤 URL"""
        if not self.config.get('auto_save_urls', True):
            return
            
        try:
            urls = []
            for item in self.url_tree.get_children():
                values = self.url_tree.item(item, 'values')
                urls.append(values[0])
            
            with open(self.urls_file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(urls))
        except Exception as e:
            self.log(f"❌ 自動儲存 URL 失敗: {e}")

    def update_url_count(self):
        """更新 URL 計數"""
        total = len(self.url_tree.get_children())
        valid = 0
        invalid = 0
        
        for item in self.url_tree.get_children():
            status = self.url_tree.item(item, 'values')[1]
            if '✅' in status:
                valid += 1
            elif '❌' in status:
                invalid += 1
        
        self.url_count_var.set(f"URL 數量: {total}")
        self.valid_count_var.set(f"有效: {valid}")
        self.invalid_count_var.set(f"無效: {invalid}")

    def add_url(self):
        """新增單一 URL"""
        def add():
            url = entry.get().strip()
            if url:
                if not url.startswith(('http://', 'https://')):
                    url = 'https://' + url
                
                if not self.is_valid_zozo_url(url):
                    messagebox.showwarning("格式錯誤", "請輸入有效的 ZOZO Town 商品 URL")
                    return
                
                self.add_url_to_tree(url)
                entry.delete(0, tk.END)
                self.update_url_count()
                self.save_tracked_urls()
                self.log(f"➕ 已新增 URL: {url}")
                
                # 如果啟用自動驗證
                if self.validate_urls_var.get():
                    items = self.url_tree.get_children()
                    if items:
                        threading.Thread(
                            target=self.validate_urls_worker,
                            args=([items[-1]],),
                            daemon=True
                        ).start()
                
                dialog.destroy()
            
        dialog = tk.Toplevel(self.root)
        dialog.title("新增 ZOZO 商品 URL")
        dialog.geometry("600x180")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="輸入 ZOZO Town 商品 URL:", font=("Arial", 10)).pack(padx=10, pady=10)
        
        entry = ttk.Entry(dialog, width=70, font=("Arial", 9))
        entry.pack(padx=10, pady=5, fill='x')
        entry.focus_set()
        
        example_label = ttk.Label(
            dialog,
            text="例如: https://zozo.jp/shop/beams/goods/74917621/",
            font=("Arial", 8),
            foreground="gray"
        )
        example_label.pack(padx=10, pady=2)
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(padx=10, pady=15)
        
        ttk.Button(btn_frame, text="新增", command=add).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side='left', padx=5)
        
        entry.bind('<Return>', lambda e: add())

    def remove_selected_urls(self):
        """移除所選 URL"""
        selected = self.url_tree.selection()
        if not selected:
            messagebox.showinfo("提示", "請先選擇要移除的 URL")
            return
            
        for item in selected:
            self.url_tree.delete(item)
            
        self.update_url_count()
        self.save_tracked_urls()
        self.log(f"🗑️ 已移除 {len(selected)} 個 URL")

    def clear_all_urls(self):
        """清空所有 URL"""
        if not self.url_tree.get_children():
            messagebox.showinfo("提示", "URL 列表已經是空的")
            return
            
        if messagebox.askyesno("確認", "確定要清空所有 URL 嗎？"):
            count = len(self.url_tree.get_children())
            for item in self.url_tree.get_children():
                self.url_tree.delete(item)
            self.update_url_count()
            self.save_tracked_urls()
            self.log(f"🧹 已清空 {count} 個 URL")

    def load_url_file(self):
        """載入 URL 檔案"""
        filepath = filedialog.askopenfilename(
            title="選擇 URL 檔案",
            filetypes=[("文字檔案", "*.txt"), ("所有檔案", "*.*")]
        )
        if filepath:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    urls = [line.strip() for line in f if line.strip()]
                
                # 清空現有項目
                for item in self.url_tree.get_children():
                    self.url_tree.delete(item)
                
                # 新增 URL
                for url in urls:
                    self.add_url_to_tree(url)
                
                self.urls_file_path = filepath
                self.update_url_count()
                self.log(f"📂 已載入 {len(urls)} 個 URL 從 {os.path.basename(filepath)}")
            except Exception as e:
                self.log(f"❌ 載入 URL 檔案失敗: {e}")

    def save_url_file(self):
        """儲存 URL 檔案"""
        urls = [self.url_tree.item(item, 'values')[0] for item in self.url_tree.get_children()]
        if not urls:
            messagebox.showinfo("提示", "沒有 URL 可儲存")
            return
            
        filepath = filedialog.asksaveasfilename(
            title="儲存 URL 檔案",
            defaultextension=".txt",
            filetypes=[("文字檔案", "*.txt"), ("所有檔案", "*.*")],
            initialfile="zozo_tracked_urls.txt"
        )
        if filepath:
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(urls))
                self.log(f"💾 已儲存 {len(urls)} 個 URL 至 {os.path.basename(filepath)}")
            except Exception as e:
                self.log(f"❌ 儲存 URL 檔案失敗: {e}")

    def start_sync(self):
        """開始同步折扣"""
        urls = [self.url_tree.item(item, 'values')[0] for item in self.url_tree.get_children()]
        if not urls:
            messagebox.showwarning("注意", "請先添加至少一筆 ZOZO URL！")
            return
        
        if self.is_syncing:
            messagebox.showwarning("提示", "同步正在進行中...")
            return
        
        # 確認開始同步
        if not messagebox.askyesno(
            "確認同步",
            f"即將同步 {len(urls)} 個 ZOZO 商品的折扣到 Easy Store。\n\n"
            f"高價商品額外折扣: {'啟用' if self.high_price_var.get() else '停用'}\n"
            f"自動重試: {'啟用' if self.auto_retry_var.get() else '停用'}\n\n"
            f"確定開始？"
        ):
            return
        
        # 備份設定
        if self.backup_var.get():
            self.backup_config()
        
        # 重置進度條和結果
        self.progress_var.set(0)
        self.progress['maximum'] = len(urls)
        self.sync_results = []
        self.is_syncing = True
        
        # 更新 UI 狀態
        self.status_var.set("🔄 同步中...")
        self.disable_buttons()
        
        # 啟動同步線程
        threading.Thread(
            target=self.sync_worker,
            args=(urls, self.high_price_var.get()),
            daemon=True
        ).start()

    def sync_worker(self, urls, apply_additional_discount):
        """同步處理線程 - 增強版"""
        
        if not self.zozo_logged_in:
            self.root.after(0, lambda: self.log("警告：尚未登入 ZOZO 會員，可能無法獲取會員折扣", "WARNING"))
        
        total = len(urls)
        completed = 0
        success_count = 0
        fail_count = 0
        failed_urls = []
        
        self.root.after(0, lambda: self.log(f"🚀 開始同步 {total} 個 ZOZO 商品..."))
        
        try:
            for i, url in enumerate(urls):
                if not self.is_syncing:  # 檢查是否被停止
                    break
                    
                completed += 1
                current_item = None
                
                # 找到對應的樹狀項目
                for item in self.url_tree.get_children():
                    if self.url_tree.item(item, 'values')[0] == url:
                        current_item = item
                        break
                
                try:
                    # 更新狀態
                    self.root.after(0, lambda c=completed, t=total:
                                  self.status_var.set(f"🔄 同步中... ({c}/{t})"))
                    
                    self.root.after(0, lambda: self.progress_text_var.set(f"處理中: {url[:50]}..."))
                    
                    if current_item:
                        self.root.after(0, lambda i=current_item: self.url_tree.set(i, 'status', '🔄 處理中'))
                    
                    # 同步折扣
                    self.root.after(0, lambda u=url, c=completed, t=total:
                                  self.log(f"📝 處理 [{c}/{t}] {u}"))
                    
                    result = self.syncer.sync_discount(url, apply_additional_discount)
                    
                    # 儲存結果
                    self.sync_results.append(result)
                    
                    # 更新日誌和 UI
                    if result['success']:
                        success_count += 1
                        
                        log_msg = (f"✅ [成功] {result['zozo_sku']} -> {result['easy_sku']} - "
                                 f"ZOZO {result['zozo_discount']}% -> Easy {result['easy_discount']}%, "
                                 f"更新了 {result['updated_variants_count']} 個變體")
                        
                        if result.get('additional_discount_applied'):
                            log_msg += f" (含高價商品額外折扣)"
                            
                        self.root.after(0, lambda msg=log_msg: self.log(msg, "SUCCESS"))
                        
                        # 更新樹狀列表
                        if current_item:
                            current_time = datetime.now().strftime("%m-%d %H:%M")
                            discount_text = f"{result['easy_discount']}%"
                            self.root.after(0, lambda i=current_item, t=current_time, d=discount_text: (
                                self.url_tree.set(i, 'status', '✅ 成功'),
                                self.url_tree.set(i, 'last_sync', t),
                                self.url_tree.set(i, 'discount', d)
                            ))
                    else:
                        fail_count += 1
                        failed_urls.append(url)
                        error_msg = result.get('error', '未知錯誤')
                        
                        self.root.after(0, lambda err=error_msg, u=url:
                                      self.log(f"❌ [失敗] {u} - {err}", "ERROR"))
                        
                        if current_item:
                            self.root.after(0, lambda i=current_item: self.url_tree.set(i, 'status', '❌ 失敗'))
                    
                    # 更新進度條
                    self.root.after(0, lambda: self.progress_var.set(completed))
                    
                except Exception as e:
                    fail_count += 1
                    failed_urls.append(url)
                    self.root.after(0, lambda err=str(e), u=url:
                                  self.log(f"💥 [錯誤] 處理 {u} 時發生異常: {err}", "ERROR"))
                    
                    if current_item:
                        self.root.after(0, lambda i=current_item: self.url_tree.set(i, 'status', '💥 錯誤'))
                
                # 短暫延遲避免過於頻繁的請求
                time.sleep(1)
            
            # 自動重試失敗的項目
            if failed_urls and self.auto_retry_var.get() and self.is_syncing:
                retry_count = self.retry_count_var.get()
                retry_delay = self.retry_delay_var.get()
                
                self.root.after(0, lambda: self.log(f"🔄 開始自動重試 {len(failed_urls)} 個失敗項目..."))
                
                for retry_attempt in range(retry_count):
                    if not self.is_syncing:
                        break
                        
                    retry_failed = []
                    self.root.after(0, lambda a=retry_attempt+1: self.log(f"🔄 第 {a} 次重試..."))
                    
                    for url in failed_urls:
                        if not self.is_syncing:
                            break
                            
                        try:
                            time.sleep(retry_delay)
                            result = self.syncer.sync_discount(url, apply_additional_discount)
                            
                            if result['success']:
                                success_count += 1
                                fail_count -= 1
                                self.root.after(0, lambda u=url: self.log(f"✅ 重試成功: {u}", "SUCCESS"))
                                
                                # 更新對應的樹狀項目
                                for item in self.url_tree.get_children():
                                    if self.url_tree.item(item, 'values')[0] == url:
                                        current_time = datetime.now().strftime("%m-%d %H:%M")
                                        discount_text = f"{result['easy_discount']}%"
                                        self.root.after(0, lambda i=item, t=current_time, d=discount_text: (
                                            self.url_tree.set(i, 'status', '✅ 成功'),
                                            self.url_tree.set(i, 'last_sync', t),
                                            self.url_tree.set(i, 'discount', d)
                                        ))
                                        break
                            else:
                                retry_failed.append(url)
                                
                        except Exception as e:
                            retry_failed.append(url)
                            self.root.after(0, lambda u=url, err=str(e):
                                          self.log(f"❌ 重試失敗: {u} - {err}", "ERROR"))
                    
                    failed_urls = retry_failed
                    if not failed_urls:
                        break
                        
        except Exception as e:
            self.root.after(0, lambda err=str(e): self.log(f"💥 [嚴重錯誤] 同步過程中斷: {err}", "ERROR"))
        finally:
            self.is_syncing = False
            
            # 完成處理
            self.root.after(0, lambda: self.log(f"🎉 同步完成! 共處理 {total} 個 URL，成功 {success_count} 個，失敗 {fail_count} 個", "SUCCESS"))
            self.root.after(0, lambda: self.status_var.set("✅ 同步完成"))
            self.root.after(0, lambda: self.progress_text_var.set(""))
            
            # 顯示結果
            self.root.after(0, lambda: messagebox.showinfo(
                "同步完成",
                f"ZOZO 折扣同步已完成！\n\n"
                f"總數: {total}\n"
                f"成功: {success_count}\n"
                f"失敗: {fail_count}\n"
                f"成功率: {success_count/total*100:.1f}%"
            ))
            
            # 恢復按鈕
            self.root.after(0, self.enable_buttons)

    def test_single_product(self):
        """測試單一商品 - 增強版"""
        def test():
            url = entry.get().strip()
            if not url:
                messagebox.showwarning("提示", "請輸入 URL")
                return
                
            if not self.is_valid_zozo_url(url):
                messagebox.showwarning("格式錯誤", "請輸入有效的 ZOZO Town 商品 URL")
                return
                
            dialog.destroy()
            
            # 開始測試
            self.log(f"🧪 開始測試商品: {url}")
            self.disable_buttons()
            self.status_var.set("🧪 測試中...")
            
            threading.Thread(
                target=self.test_single_worker,
                args=(url,),
                daemon=True
            ).start()
        
        dialog = tk.Toplevel(self.root)
        dialog.title("測試單一商品")
        dialog.geometry("650x200")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 使用更好的佈局
        main_frame = ttk.Frame(dialog)
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        
        ttk.Label(
            main_frame,
            text="輸入要測試的 ZOZO Town 商品 URL:",
            font=("Arial", 11)
        ).pack(anchor='w', pady=(0, 10))
        
        entry = ttk.Entry(main_frame, width=70, font=("Arial", 9))
        entry.pack(fill='x', pady=(0, 5))
        entry.focus_set()
        
        example_label = ttk.Label(
            main_frame,
            text="例如: https://zozo.jp/shop/beams/goods/74917621/",
            font=("Arial", 8),
            foreground="gray"
        )
        example_label.pack(anchor='w', pady=(0, 15))
        
        # 測試選項
        options_frame = ttk.LabelFrame(main_frame, text="測試選項")
        options_frame.pack(fill='x', pady=(0, 15))
        
        test_high_price_var = tk.BooleanVar(value=self.high_price_var.get())
        ttk.Checkbutton(
            options_frame,
            text="模擬高價商品額外折扣",
            variable=test_high_price_var
        ).pack(anchor='w', padx=10, pady=5)
        
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack()
        
        ttk.Button(
            btn_frame,
            text="🧪 開始測試",
            command=lambda: test() if entry.get().strip() else None
        ).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="取消", command=dialog.destroy).pack(side='left', padx=5)
        
        entry.bind('<Return>', lambda e: test())

    def test_single_worker(self, url):
        """測試單一商品的工作線程 - 增強版"""
        try:
            start_time = time.time()
            result = self.syncer.sync_discount(url, self.high_price_var.get())
            end_time = time.time()
            
            processing_time = end_time - start_time
            
            if result['success']:
                self.root.after(0, lambda: self.log(f"✅ [測試成功] {result['zozo_sku']} -> {result['easy_sku']}", "SUCCESS"))
                self.root.after(0, lambda: self.log(f"📊 折扣: ZOZO {result['zozo_discount']}% -> Easy {result['easy_discount']}%"))
                self.root.after(0, lambda: self.log(f"🔧 更新了 {result['updated_variants_count']} 個變體"))
                self.root.after(0, lambda: self.log(f"⏱️ 處理時間: {processing_time:.1f} 秒"))
                
                # 詳細結果對話框
                detail_msg = (
                    f"商品測試成功！\n\n"
                    f"🏷️ ZOZO SKU: {result['zozo_sku']}\n"
                    f"🏪 Easy SKU: {result['easy_sku']}\n"
                    f"💰 折扣: {result['zozo_discount']}% → {result['easy_discount']}%\n"
                    f"🔧 更新變體數: {result['updated_variants_count']}\n"
                    f"💵 原價: ¥{result.get('original_price', 'N/A')}\n"
                    f"💸 最終價格: ¥{result.get('final_price', 'N/A')}\n"
                    f"⚡ 高價折扣: {'是' if result.get('additional_discount_applied') else '否'}\n"
                    f"⏱️ 處理時間: {processing_time:.1f} 秒"
                )
                
                self.root.after(0, lambda: messagebox.showinfo("測試成功", detail_msg))
            else:
                error_msg = result['error']
                self.root.after(0, lambda: self.log(f"❌ [測試失敗] {error_msg}", "ERROR"))
                self.root.after(0, lambda: messagebox.showerror("測試失敗", f"測試失敗:\n\n{error_msg}"))
                
        except Exception as e:
            self.root.after(0, lambda: self.log(f"💥 [測試錯誤] {str(e)}", "ERROR"))
            self.root.after(0, lambda: messagebox.showerror("測試錯誤", f"測試過程發生錯誤:\n\n{str(e)}"))
        finally:
            self.root.after(0, lambda: self.status_var.set("🟢 就緒"))
            self.root.after(0, self.enable_buttons)

    def restore_original_prices(self):
        """還原商品到原價 - 增強版"""
        urls = [self.url_tree.item(item, 'values')[0] for item in self.url_tree.get_children()]
        if not urls:
            messagebox.showwarning("注意", "請先添加至少一筆 URL！")
            return
        
        if self.is_syncing:
            messagebox.showwarning("提示", "操作正在進行中...")
            return
        
        # 確認操作
        if not messagebox.askyesno(
            "確認操作",
            f"此操作將把 {len(urls)} 個商品的價格還原為原價 (無折扣)。\n\n"
            f"這個操作無法撤銷，確定繼續嗎？",
            icon='warning'
        ):
            return
        
        # 重置進度條
        self.progress_var.set(0)
        self.progress['maximum'] = len(urls)
        self.sync_results = []
        self.is_syncing = True
        
        # 更新 UI 狀態
        self.status_var.set("🔙 還原中...")
        self.disable_buttons()
        
        # 啟動還原線程
        threading.Thread(
            target=self.restore_worker,
            args=(urls,),
            daemon=True
        ).start()

    def restore_worker(self, urls):
        """還原價格處理線程 - 增強版"""
        total = len(urls)
        completed = 0
        success_count = 0
        fail_count = 0
        
        self.root.after(0, lambda: self.log(f"🔙 開始還原 {total} 個商品的原價...", "INFO"))
        
        try:
            for url in urls:
                if not self.is_syncing:  # 檢查是否被停止
                    break
                    
                completed += 1
                current_item = None
                
                # 找到對應的樹狀項目
                for item in self.url_tree.get_children():
                    if self.url_tree.item(item, 'values')[0] == url:
                        current_item = item
                        break
                
                try:
                    # 更新狀態
                    self.root.after(0, lambda c=completed, t=total:
                                  self.status_var.set(f"🔙 還原中... ({c}/{t})"))
                    
                    self.root.after(0, lambda: self.progress_text_var.set(f"還原中: {url[:50]}..."))
                    
                    if current_item:
                        self.root.after(0, lambda i=current_item: self.url_tree.set(i, 'status', '🔙 還原中'))
                    
                    # 還原原價
                    self.root.after(0, lambda u=url, c=completed, t=total:
                                  self.log(f"📝 處理 [{c}/{t}] {u}"))
                    
                    result = self.syncer.restore_original_prices(url)
                    
                    # 儲存結果
                    self.sync_results.append(result)
                    
                    # 更新日誌
                    if result['success']:
                        success_count += 1
                        self.root.after(0, lambda r=result:
                                      self.log(f"✅ [成功] {r['zozo_sku']} -> {r['easy_sku']} - "
                                             f"已還原 {r['restored_variants_count']} 個變體的原價", "SUCCESS"))
                        
                        # 更新樹狀列表
                        if current_item:
                            current_time = datetime.now().strftime("%m-%d %H:%M")
                            self.root.after(0, lambda i=current_item, t=current_time: (
                                self.url_tree.set(i, 'status', '🔙 已還原'),
                                self.url_tree.set(i, 'last_sync', t),
                                self.url_tree.set(i, 'discount', '原價')
                            ))
                    else:
                        fail_count += 1
                        error_msg = result.get('error', '未知錯誤')
                        self.root.after(0, lambda err=error_msg, u=url:
                                      self.log(f"❌ [失敗] {u} - {err}", "ERROR"))
                        
                        if current_item:
                            self.root.after(0, lambda i=current_item: self.url_tree.set(i, 'status', '❌ 失敗'))
                    
                    # 更新進度條
                    self.root.after(0, lambda: self.progress_var.set(completed))
                    
                except Exception as e:
                    fail_count += 1
                    self.root.after(0, lambda err=str(e), u=url:
                                  self.log(f"💥 [錯誤] 處理 {u} 時發生異常: {err}", "ERROR"))
                    
                    if current_item:
                        self.root.after(0, lambda i=current_item: self.url_tree.set(i, 'status', '💥 錯誤'))
                
                # 短暫延遲
                time.sleep(0.5)
            
        except Exception as e:
            self.root.after(0, lambda err=str(e): self.log(f"💥 [嚴重錯誤] 還原過程中斷: {err}", "ERROR"))
        finally:
            self.is_syncing = False
            
            # 完成處理
            self.root.after(0, lambda: self.log(f"🎉 還原完成! 共處理 {total} 個 URL，成功 {success_count} 個，失敗 {fail_count} 個", "SUCCESS"))
            self.root.after(0, lambda: self.status_var.set("✅ 還原完成"))
            self.root.after(0, lambda: self.progress_text_var.set(""))
            
            # 顯示結果
            self.root.after(0, lambda: messagebox.showinfo(
                "還原完成",
                f"商品原價還原已完成！\n\n"
                f"總數: {total}\n"
                f"成功: {success_count}\n"
                f"失敗: {fail_count}\n"
                f"成功率: {success_count/total*100:.1f}%"
            ))
            
            # 恢復按鈕
            self.root.after(0, self.enable_buttons)

    def stop_operation(self):
        """停止當前操作"""
        if self.is_syncing:
            if messagebox.askyesno("確認", "確定要停止當前操作嗎？"):
                self.is_syncing = False
                self.log("⏹️ 用戶手動停止操作", "WARNING")
                self.status_var.set("⏹️ 已停止")
                self.enable_buttons()

    def backup_config(self):
        """備份設定檔"""
        try:
            backup_dir = "backups"
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(backup_dir, f"zozo_config_backup_{timestamp}.json")
            
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            
            self.log(f"💾 設定已備份至: {backup_file}")
        except Exception as e:
            self.log(f"❌ 備份設定失敗: {e}", "ERROR")

    def log(self, msg, level="INFO"):
        """添加日誌訊息 - 增強版"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # 輸出到控制台
        print(f"[{timestamp}] {level}: {msg}")
        
        # 輸出到 GUI
        if hasattr(self, 'log_box') and self.log_box:
            try:
                # 根據等級設定標籤
                tag = level if level in ["INFO", "SUCCESS", "WARNING", "ERROR", "DEBUG"] else "INFO"
                
                log_line = f"[{timestamp}] {msg}\n"
                self.log_box.insert(tk.END, log_line, tag)
                self.log_box.see(tk.END)
                self.root.update_idletasks()
            except Exception as e:
                print(f"無法寫入 GUI 日誌: {e}")

    def filter_logs(self, event=None):
        """過濾日誌顯示"""
        # 這是簡化版本，實際實現需要更複雜的日誌管理
        level = self.log_level_var.get()
        if level == "全部":
            return
        
        # 可以擴展為實際的日誌過濾功能
        self.log(f"🔍 已設定日誌過濾等級: {level}")

    def search_log(self):
        """搜尋日誌"""
        search_term = simpledialog.askstring("搜尋日誌", "輸入搜尋關鍵字:")
        if search_term:
            content = self.log_box.get(1.0, tk.END)
            if search_term.lower() in content.lower():
                # 簡單的搜尋高亮，可以擴展為更複雜的功能
                self.log(f"🔍 在日誌中找到關鍵字: {search_term}")
            else:
                self.log(f"🔍 未在日誌中找到關鍵字: {search_term}")

    def save_log(self):
        """儲存日誌到檔案"""
        content = self.log_box.get(1.0, tk.END)
        if not content.strip():
            messagebox.showinfo("提示", "沒有日誌內容可儲存")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = filedialog.asksaveasfilename(
            title="儲存日誌",
            defaultextension=".txt",
            filetypes=[("文字檔案", "*.txt"), ("所有檔案", "*.*")],
            initialfile=f"zozo_sync_log_{timestamp}.txt"
        )
        
        if filepath:
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.log(f"💾 日誌已儲存至: {os.path.basename(filepath)}")
            except Exception as e:
                self.log(f"❌ 儲存日誌失敗: {e}", "ERROR")

    def clear_log(self):
        """清空日誌"""
        if messagebox.askyesno("確認", "確定要清空所有日誌嗎？"):
            self.log_box.delete(1.0, tk.END)
            self.log("🧹 日誌已清空")

    def export_results(self):
        """匯出同步結果 - 增強版"""
        if not self.sync_results:
            messagebox.showinfo("提示", "沒有同步結果可匯出")
            return
            
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = filedialog.asksaveasfilename(
            title="匯出同步結果",
            defaultextension=".xlsx",
            filetypes=[
                ("Excel檔案", "*.xlsx"),
                ("CSV檔案", "*.csv"),
                ("JSON檔案", "*.json"),
                ("所有檔案", "*.*")
            ],
            initialfile=f"ZOZO_折扣同步結果_{timestamp}.xlsx"
        )
        
        if filepath:
            try:
                # 準備匯出資料
                export_data = []
                for i, r in enumerate(self.sync_results, 1):
                    base_data = {
                        '序號': i,
                        '時間戳': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'URL': r.get('url', ''),
                        '狀態': '成功' if r.get('success', False) else '失敗'
                    }
                    
                    if r.get('success', False):
                        if 'zozo_discount' in r:  # 折扣同步
                            base_data.update({
                                '操作類型': '折扣同步',
                                'ZOZO SKU': r.get('zozo_sku', ''),
                                'Easy SKU': r.get('easy_sku', ''),
                                'ZOZO 折扣%': r.get('zozo_discount', ''),
                                'Easy 折扣%': r.get('easy_discount', ''),
                                '原價': r.get('original_price', ''),
                                '最終價格': r.get('final_price', ''),
                                '高價商品額外折扣': '是' if r.get('additional_discount_applied', False) else '否',
                                '更新變體數': r.get('updated_variants_count', ''),
                                'Product ID': r.get('product_id', ''),
                                '折扣截止': r.get('discount_deadline', ''),
                                '節省金額': r.get('original_price', 0) - r.get('final_price', 0) if r.get('original_price') and r.get('final_price') else 0
                            })
                        else:  # 原價還原
                            base_data.update({
                                '操作類型': '原價還原',
                                'ZOZO SKU': r.get('zozo_sku', ''),
                                'Easy SKU': r.get('easy_sku', ''),
                                '還原變體數': r.get('restored_variants_count', ''),
                                'Product ID': r.get('product_id', '')
                            })
                    else:
                        base_data.update({
                            '操作類型': '處理失敗',
                            '錯誤訊息': r.get('error', '')
                        })
                    
                    export_data.append(base_data)
                
                # 根據檔案類型匯出
                if filepath.endswith('.xlsx'):
                    df = pd.DataFrame(export_data)
                    
                    # 使用 ExcelWriter 創建多個工作表
                    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                        # 主要結果
                        df.to_excel(writer, sheet_name='同步結果', index=False)
                        
                        # 統計摘要
                        summary_data = {
                            '項目': ['總處理數', '成功數', '失敗數', '成功率', '總節省金額'],
                            '數值': [
                                len(self.sync_results),
                                len([r for r in self.sync_results if r.get('success')]),
                                len([r for r in self.sync_results if not r.get('success')]),
                                f"{len([r for r in self.sync_results if r.get('success')])/len(self.sync_results)*100:.1f}%",
                                sum([r.get('original_price', 0) - r.get('final_price', 0)
                                    for r in self.sync_results
                                    if r.get('success') and r.get('original_price') and r.get('final_price')])
                            ]
                        }
                        pd.DataFrame(summary_data).to_excel(writer, sheet_name='統計摘要', index=False)
                
                elif filepath.endswith('.csv'):
                    df = pd.DataFrame(export_data)
                    df.to_csv(filepath, index=False, encoding='utf-8-sig')
                
                elif filepath.endswith('.json'):
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(export_data, f, indent=4, ensure_ascii=False)
                
                self.log(f"📊 已匯出同步結果至 {os.path.basename(filepath)}", "SUCCESS")
                messagebox.showinfo("匯出成功", f"同步結果已匯出至:\n{filepath}")
                
                # 詢問是否開啟檔案
                if messagebox.askyesno("開啟檔案", "是否要開啟匯出的檔案？"):
                    try:
                        os.startfile(filepath)  # Windows
                    except:
                        try:
                            os.system(f"open '{filepath}'")  # macOS
                        except:
                            os.system(f"xdg-open '{filepath}'")  # Linux
                
            except Exception as e:
                self.log(f"❌ 匯出結果失敗: {e}", "ERROR")
                messagebox.showerror("匯出失敗", f"匯出結果時發生錯誤:\n{e}")

    # 排程相關功能
    def load_schedule_config(self):
        """載入排程設定"""
        try:
            if os.path.exists(self.schedule_file):
                with open(self.schedule_file, 'r', encoding='utf-8') as f:
                    schedule_config = json.load(f)
                    self.enable_schedule_var.set(schedule_config.get('enabled', False))
                    self.schedule_interval_var.set(schedule_config.get('interval', 60))
        except Exception as e:
            self.log(f"❌ 載入排程設定失敗: {e}", "ERROR")

    def save_schedule_config(self):
        """儲存排程設定"""
        try:
            schedule_config = {
                'enabled': self.enable_schedule_var.get(),
                'interval': self.schedule_interval_var.get()
            }
            with open(self.schedule_file, 'w', encoding='utf-8') as f:
                json.dump(schedule_config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            self.log(f"❌ 儲存排程設定失敗: {e}", "ERROR")

    def toggle_schedule(self):
        """切換排程狀態"""
        if self.enable_schedule_var.get():
            self.start_schedule()
        else:
            self.stop_schedule_func()

    def start_schedule(self):
        """啟動排程"""
        if self.schedule_thread and self.schedule_thread.is_alive():
            self.log("⚠️ 排程已在運行中", "WARNING")
            return
        
        self.stop_schedule = False
        self.schedule_thread = threading.Thread(target=self.schedule_worker, daemon=True)
        self.schedule_thread.start()
        
        self.schedule_status_var.set("▶️ 運行中")
        self.start_schedule_btn.configure(state='disabled')
        self.stop_schedule_btn.configure(state='normal')
        
        self.save_schedule_config()
        self.log("▶️ 自動排程已啟動", "SUCCESS")

    def stop_schedule_func(self):
        """停止排程"""
        self.stop_schedule = True
        self.enable_schedule_var.set(False)
        
        self.schedule_status_var.set("⏹️ 未啟用")
        self.start_schedule_btn.configure(state='normal')
        self.stop_schedule_btn.configure(state='disabled')
        self.next_run_var.set("")
        
        self.save_schedule_config()
        self.log("⏹️ 自動排程已停止", "WARNING")

    def schedule_worker(self):
        """排程工作線程"""
        while not self.stop_schedule:
            try:
                interval_minutes = self.schedule_interval_var.get()
                next_run = datetime.now() + timedelta(minutes=interval_minutes)
                
                # 更新下次執行時間
                self.root.after(0, lambda: self.next_run_var.set(f"下次執行: {next_run.strftime('%H:%M:%S')}"))
                
                # 等待到執行時間
                for remaining in range(interval_minutes * 60, 0, -1):
                    if self.stop_schedule:
                        return
                    
                    time.sleep(1)
                    
                    # 每分鐘更新一次顯示
                    if remaining % 60 == 0:
                        minutes_left = remaining // 60
                        self.root.after(0, lambda m=minutes_left:
                                      self.next_run_var.set(f"下次執行: {m} 分鐘後"))
                
                if self.stop_schedule:
                    return
                
                # 執行同步
                self.root.after(0, lambda: self.log("⏰ 排程觸發自動同步", "INFO"))
                
                urls = []
                for item in self.url_tree.get_children():
                    values = self.url_tree.item(item, 'values')
                    urls.append(values[0])
                
                if urls and not self.is_syncing:
                    # 記錄排程執行
                    start_time = datetime.now()
                    
                    # 執行同步（簡化版，不更新 UI 進度）
                    success_count = 0
                    fail_count = 0
                    
                    for url in urls:
                        if self.stop_schedule:
                            break
                        try:
                            result = self.syncer.sync_discount(url, self.high_price_var.get())
                            if result['success']:
                                success_count += 1
                            else:
                                fail_count += 1
                        except:
                            fail_count += 1
                    
                    # 更新排程歷史
                    history_item = (
                        start_time.strftime('%Y-%m-%d %H:%M:%S'),
                        '完成',
                        len(urls),
                        success_count,
                        fail_count
                    )
                    
                    self.root.after(0, lambda: self.history_tree.insert('', 0, values=history_item))
                    self.root.after(0, lambda: self.log(f"⏰ 排程同步完成: 成功 {success_count}, 失敗 {fail_count}", "SUCCESS"))
                
            except Exception as e:
                self.root.after(0, lambda err=str(e): self.log(f"❌ 排程執行錯誤: {err}", "ERROR"))

    def update_stats(self):
        """更新統計資料"""
        try:
            # 這裡可以實現統計資料的計算
            # 目前是簡化版本
            
            total_syncs = len(self.sync_results)
            successful_syncs = len([r for r in self.sync_results if r.get('success')])
            failed_syncs = total_syncs - successful_syncs
            
            # 計算總節省金額
            total_savings = sum([
                r.get('original_price', 0) - r.get('final_price', 0)
                for r in self.sync_results
                if r.get('success') and r.get('original_price') and r.get('final_price')
            ])
            
            # 計算平均折扣
            discounts = [r.get('easy_discount', 0) for r in self.sync_results if r.get('success') and r.get('easy_discount')]
            avg_discount = sum(discounts) / len(discounts) if discounts else 0
            
            # 最後同步時間
            last_sync = max([
                r.get('timestamp', datetime.min)
                for r in self.sync_results
                if r.get('success')
            ], default=datetime.min)
            
            # 更新顯示
            self.stats_labels['total_syncs'].config(text=str(total_syncs))
            self.stats_labels['successful_syncs'].config(text=str(successful_syncs))
            self.stats_labels['failed_syncs'].config(text=str(failed_syncs))
            self.stats_labels['total_savings'].config(text=f"¥{total_savings:,.0f}")
            self.stats_labels['avg_discount'].config(text=f"{avg_discount:.1f}%")
            self.stats_labels['last_sync'].config(
                text=last_sync.strftime('%Y-%m-%d %H:%M') if last_sync != datetime.min else '無'
            )
            
            self.log("📊 統計資料已更新", "SUCCESS")
            
        except Exception as e:
            self.log(f"❌ 更新統計失敗: {e}", "ERROR")

    def disable_buttons(self):
        """禁用操作按鈕"""
        buttons_to_disable = [
            self.sync_btn, self.restore_btn, self.test_btn
        ]
        
        for btn in buttons_to_disable:
            if btn.winfo_exists():
                btn.configure(state='disabled')
        
        # 啟用停止按鈕
        for widget in self.root.winfo_children():
            self.find_and_enable_stop_button(widget)

    def enable_buttons(self):
        """啟用操作按鈕"""
        buttons_to_enable = [
            self.sync_btn, self.restore_btn, self.test_btn
        ]
        
        for btn in buttons_to_enable:
            if btn.winfo_exists():
                btn.configure(state='normal')
        
        # 禁用停止按鈕
        for widget in self.root.winfo_children():
            self.find_and_disable_stop_button(widget)
            
            
    def login_zozo_town(self):
        """ZOZO Town 會員登入"""
        self.log("開始 ZOZO Town 會員登入流程...")
        self.zozo_login_status_var.set("🔄 登入中...")
        self.disable_buttons()
        
        # 在新線程中執行登入
        threading.Thread(
            target=self.zozo_login_worker,
            daemon=True
        ).start()

    def zozo_login_worker(self):
        """ZOZO 會員登入處理線程"""
        try:
            # 呼叫 ZOZO 會員登入
            setup_zozo_session()
            
            # 更新登入狀態
            self.zozo_logged_in = True
            self.root.after(0, lambda: self.zozo_login_status_var.set("🟢 已登入"))
            self.root.after(0, lambda: self.log("ZOZO Town 會員登入成功!", "SUCCESS"))
            
        except Exception as e:
            error_message = str(e)
            self.root.after(0, lambda: self.zozo_login_status_var.set("🔴 登入失敗"))
            self.root.after(0, lambda: self.log(f"ZOZO Town 會員登入失敗: {error_message}", "ERROR"))
        finally:
            self.root.after(0, self.enable_buttons)

    def find_and_enable_stop_button(self, widget):
        """遞迴找到並啟用停止按鈕"""
        if isinstance(widget, ttk.Button) and "停止" in widget.cget('text'):
            widget.configure(state='normal')
        elif hasattr(widget, 'winfo_children'):
            for child in widget.winfo_children():
                self.find_and_enable_stop_button(child)

    def find_and_disable_stop_button(self, widget):
        """遞迴找到並禁用停止按鈕"""
        if isinstance(widget, ttk.Button) and "停止" in widget.cget('text'):
            widget.configure(state='disabled')
        elif hasattr(widget, 'winfo_children'):
            for child in widget.winfo_children():
                self.find_and_disable_stop_button(child)

    def on_closing(self):
        """關閉視窗時的處理 - 增強版"""
        try:
            # 停止排程
            if self.schedule_thread and self.schedule_thread.is_alive():
                self.stop_schedule = True
                self.log("⏹️ 停止排程中...")
                time.sleep(1)  # 給排程線程時間停止
            
            # 停止同步操作
            if self.is_syncing:
                self.is_syncing = False
                self.log("⏹️ 停止同步操作中...")
                
            try:
                cleanup_zozo_session()
                self.log("🗑️ 已清理 ZOZO 會話")
            except:
                pass
            
            # 自動儲存 URL 和設定
            self.save_tracked_urls()
            self.save_config()
            self.save_schedule_config()
            
            self.log("💾 設定已自動儲存", "SUCCESS")
            
        except Exception as e:
            print(f"關閉時發生錯誤: {e}")
        finally:
            # 關閉視窗
            self.root.destroy()
            sys.exit(0)


if __name__ == "__main__":
    # 設定 DPI 感知 (Windows)
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
    
    root = tk.Tk()
    
    # 設定主題樣式
    try:
        style = ttk.Style()
        style.theme_use('clam')  # 使用 clam 主題
        
        # 自定義樣式
        style.configure('Accent.TButton', foreground='white', background='#0078d4')
        style.map('Accent.TButton', background=[('active', '#106ebe')])
        
    except Exception as e:
        print(f"設定主題失敗: {e}")
    
    app = EnhancedZozoDiscountSyncApp(root)
    root.mainloop()
