import sys
import logging
import requests
import time
import os
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Signal, Slot, QThread, QObject, Qt
from PySide6.QtGui import QIcon

# 导入核心逻辑 (确保 core 文件夹在同一级目录)
from core.boos_driver import BoosDriver
from core import selectors
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def resource_path(relative_path):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


# ==========================================
# 1. 样式表 (Light Tech Theme - 亮色科技风)
# ==========================================
def get_stylesheet() -> str:
    return """
    * {
        font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
        font-size: 13px;
    }

    /* 全局背景：极简灰白 */
    QMainWindow, QWidget#Root {
        background-color: #f5f7fa;
        color: #333333;
    }

    /* 通用卡片容器：纯白背景 + 轻微边框 */
    QFrame#Card {
        background-color: #ffffff;
        border: 1px solid #e4e7ed;
        border-radius: 10px;
    }

    /* 卡片标题：深色加粗 + 底部蓝色线条装饰 */
    QLabel#CardTitle {
        color: #1f2937;
        font-size: 15px;
        font-weight: 700;
        padding-bottom: 12px;
        border-bottom: 2px solid #f0f2f5; 
        margin-bottom: 12px;
    }

    /* 普通文本标签 */
    QLabel {
        color: #606266;
    }
    
    /* 状态文字 */
    QLabel#StatusLabel {
        color: #909399;
        font-size: 12px;
        font-weight: 500;
    }

    /* 二维码占位符：浅灰背景 + 虚线框 */
    QLabel#QrPlaceholder {
        background-color: #f9fafb;
        border: 2px dashed #dcdfe6;
        border-radius: 8px;
        color: #c0c4cc;
        font-weight: bold;
    }

    /* 输入框 & 数字微调器 */
    QSpinBox {
        background-color: #ffffff;
        border: 1px solid #dcdfe6;
        border-radius: 6px;
        padding: 6px 10px;
        color: #333333;
        font-weight: bold;
    }
    QSpinBox:focus {
        border: 1px solid #3b82f6; /* 聚焦时亮蓝边框 */
        background-color: #f0f9ff;
    }
    QSpinBox::up-button, QSpinBox::down-button {
        background: transparent;
        border: none;
    }

    /* 按钮通用样式 */
    QPushButton {
        padding: 8px 18px;
        border-radius: 6px;
        font-weight: 600;
        font-size: 13px;
        border: none;
    }
    
    /* 主按钮：科技蓝渐变/纯色 */
    QPushButton#PrimaryBtn {
        background-color: #3b82f6;
        color: #ffffff;
    }
    QPushButton#PrimaryBtn:hover {
        background-color: #2563eb; /* 深一点的蓝 */
    }
    QPushButton#PrimaryBtn:pressed {
        background-color: #1d4ed8;
    }
    QPushButton#PrimaryBtn:disabled {
        background-color: #bfdbfe;
        color: #ffffff;
    }

    /* 危险/次要按钮：淡红/红色 */
    QPushButton#DangerBtn {
        background-color: #fee2e2;
        color: #ef4444;
        border: 1px solid #fecaca;
    }
    QPushButton#DangerBtn:hover {
        background-color: #fecaca;
        color: #dc2626;
    }
    QPushButton#DangerBtn:pressed {
        background-color: #fca5a5;
    }
    QPushButton#DangerBtn:disabled {
        background-color: #f3f4f6;
        color: #d1d5db;
        border: 1px solid #e5e7eb;
    }

    /* 日志框：仿IDE风格，白底黑字 */
    QPlainTextEdit {
        background-color: #ffffff;
        border: 1px solid #e4e7ed;
        border-radius: 0 0 10px 10px;
        color: #333333;
        font-family: "Consolas", "Monaco", monospace;
        font-size: 12px;
        padding: 10px;
        line-height: 1.4;
    }
    
    /* 滚动条美化 */
    QScrollBar:vertical {
        background: #f5f7fa;
        width: 8px;
        margin: 0;
        border-radius: 4px;
    }
    QScrollBar::handle:vertical {
        background: #dcdfe6;
        border-radius: 4px;
        min-height: 20px;
    }
    QScrollBar::handle:vertical:hover {
        background: #c0c4cc;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }

    /* 选项卡 (Tab Widget) */
    QTabWidget::pane {
        border: 1px solid #e4e7ed;
        border-radius: 8px;
        background-color: #ffffff;
        top: -1px;
    }
    QTabBar::tab {
        background: #f5f7fa;
        color: #606266;
        padding: 8px 20px;
        border: 1px solid #e4e7ed;
        border-bottom: none;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        margin-right: 4px;
    }
    QTabBar::tab:selected {
        background: #ffffff;
        color: #3b82f6; /* 选中时文字变蓝 */
        border-bottom: 2px solid #ffffff; /* 遮住下面的线 */
        font-weight: bold;
    }
    QTabBar::tab:hover {
        background: #eef2f6;
    }
    
    /* 分割条 */
    QSplitter::handle {
        background-color: #e4e7ed;
    }
    """


# ==========================================
# 2. 信号与日志处理
# ==========================================
class LogSignal(QObject):
    append_log = Signal(str)


class QPlainTextEditLogger(logging.Handler):
    def __init__(self, widget):
        super().__init__()
        self.widget = widget
        self.signal_emitter = LogSignal()
        self.signal_emitter.append_log.connect(self.widget.appendPlainText)

    def emit(self, record):
        try:
            msg = self.format(record)
            self.signal_emitter.append_log.emit(msg)
        except Exception:
            pass


class WorkerSignals(QObject):
    log_message = Signal(str)
    update_status = Signal(str)
    qr_code_url = Signal(str)
    login_success = Signal()
    logout_success = Signal()
    task_finished = Signal()
    error_occurred = Signal(str)


# ==========================================
# 3. 核心业务逻辑 (Driver & Worker)
# ==========================================
class GuiBoosDriver(BoosDriver):
    def __init__(self, signals, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.signals = signals
        self._stop_flag = False

    def _get_qrcode(self):
        self.logger.info("正在获取二维码...")
        try:
            wait = WebDriverWait(self.driver, 20)
            qr_code = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, selectors.QRCODE_IMG_CSS)))
            wait.until(lambda driver: qr_code.size["width"] > 0)
            url = qr_code.get_attribute("src")
            self.signals.qr_code_url.emit(url)
        except Exception as e:
            self.logger.error(f"获取二维码失败: {str(e)}")

    def _run_browse_loop(self, max_minutes: int = 20):
        self.logger.info(f"准备刷浏览量，限时 {max_minutes} 分钟...")
        self._scroll_down_list()

        cards = []
        for selector in selectors.CARD_SELECTOR_CANDIDATES:
            frame, els = self._find_cards_any_frame(selector)
            if els:
                cards = [e for e in els if e.is_displayed()]
                if cards: break

        if cards:
            self._safe_click(cards[0])
            time.sleep(3)
        else:
            self.logger.warning("未找到卡片")
            return

        self.logger.info("开始自动翻页...")
        start_time = time.time()
        end_time = start_time + (max_minutes * 60)

        while time.time() < end_time:
            if self._stop_flag:
                self.logger.info("用户停止了任务")
                break
            self._turn_page_right_detail()
            time.sleep(3)

        if not self._stop_flag:
            self.logger.info("任务时间结束")
        self._close_detail_page()

    def _run_greet_loop(self, target_count: int):
        self.logger.info(f"开始自动打招呼，目标：{target_count}人")
        greeted_count = 0
        processed_ids = set()

        while greeted_count < target_count:
            if self._stop_flag:
                self.logger.info("用户停止了任务")
                break

            cards = []
            for selector in selectors.CARD_SELECTOR_CANDIDATES:
                frame, els = self._find_cards_any_frame(selector)
                if els:
                    cards = [e for e in els if e.is_displayed()]
                    if cards: break

            if not cards:
                self.logger.warning("向下滚动刷新...")
                self._scroll_down_list()
                continue

            target_card = None
            target_id = None
            for card in cards:
                if self._stop_flag: break
                try:
                    gid = card.get_attribute("data-geekid")
                    if gid in processed_ids: continue
                    text = card.text
                    has_kw = any(k in text for k in self.target_keywords)
                    is_online = False
                    try:
                        icon = card.find_element(By.CSS_SELECTOR, ".online-marker")
                        if icon.is_displayed(): is_online = True
                    except:
                        pass

                    if has_kw and is_online:
                        target_card = card
                        target_id = gid
                        self.logger.info(f"找到匹配: {text.replace(chr(10), ' ')[:15]}...")
                        break
                except:
                    continue

            if target_card:
                processed_ids.add(target_id)
                try:
                    self._safe_click(target_card)
                    status = self._perform_detail_actions()
                    if status == "LIMIT_REACHED":
                        self.logger.warning("今日沟通已达上限，停止任务")
                        break
                    elif status == "SUCCESS":
                        greeted_count += 1
                        self.logger.info(f"进度: {greeted_count}/{target_count}")
                except Exception as e:
                    self.logger.error(f"操作出错: {e}")
            else:
                self.logger.info("当前屏无合适人选，滚动...")
                self._scroll_down_list()

    def stop_task(self):
        self._stop_flag = True


class WorkerThread(QThread):
    def __init__(self):
        super().__init__()
        self.signals = WorkerSignals()
        self.driver = None
        self.action = None
        self.params = {}

    def run(self):
        try:
            if not self.driver and self.action != 'logout':
                self.driver = GuiBoosDriver(self.signals)

            if self.action == 'login':
                self._do_login()
            elif self.action == 'logout':
                self._do_logout()
            elif self.action == 'greet':
                if self.driver:
                    self.driver._stop_flag = False
                    self.driver._run_greet_loop(self.params.get('count', 5))
                    self.signals.task_finished.emit()
            elif self.action == 'browse':
                if self.driver:
                    self.driver._stop_flag = False
                    self.driver._run_browse_loop(self.params.get('minutes', 20))
                    self.signals.task_finished.emit()
        except Exception as e:
            self.signals.error_occurred.emit(str(e))

    def _do_login(self):
        try:
            self.signals.update_status.emit("正在打开浏览器...")
            self.driver.driver.get("https://www.zhipin.com/")
            applied = self.driver._inject_cookies_if_present()

            if applied > 0:
                self.signals.log_message.emit(f"检测到 {applied} 个本地 Cookie")
                self.signals.update_status.emit("验证 Cookie...")
                self.driver.driver.refresh()
                self.driver._click_login_if_present(3)

                if self.driver._has_recommend_talents_menu(timeout_seconds=5):
                    self.signals.log_message.emit("Cookie 验证成功")
                    self.driver._persist_cookies()
                    self.driver._click_recommend_talents()
                    self.signals.login_success.emit()
                    return
                else:
                    self.signals.log_message.emit("Cookie 已失效，需扫码")
            else:
                self.signals.log_message.emit("准备扫码登录")

            self.signals.update_status.emit("等待获取二维码...")
            self.driver._close_download_popup_if_present(2)
            self.driver._click_login_if_present(2)
            self.driver._click_app_scan_login()
            self.driver._get_qrcode()
            self.driver._wait_for_scan_login()
            self.driver._persist_cookies()
            self.driver._close_download_popup_if_present(2)
            self.driver._click_recommend_talents()
            self.signals.log_message.emit("扫码登录成功")
            self.signals.login_success.emit()
        except Exception as e:
            raise e

    def _do_logout(self):
        self.signals.update_status.emit("正在退出...")
        cookie_file = "cookies.json"
        if os.path.exists(cookie_file):
            try:
                os.remove(cookie_file)
            except:
                pass
        if self.driver:
            try:
                self.driver.close()
            except:
                pass
            self.driver = None
        self.signals.logout_success.emit()

    def stop_current_task(self):
        if self.driver: self.driver.stop_task()


# ==========================================
# 4. 主界面 (GUI) - 亮色科技版
# ==========================================
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Boss直聘 自动助手 Pro")
        self.resize(1080, 720)
        self.setStyleSheet(get_stylesheet())

        # 后台线程初始化
        self.worker = WorkerThread()
        self.worker.signals.qr_code_url.connect(self.display_qr_code)
        self.worker.signals.log_message.connect(self.append_log)
        self.worker.signals.update_status.connect(self.update_status_label)
        self.worker.signals.login_success.connect(self.on_login_success)
        self.worker.signals.logout_success.connect(self.on_logout_success)
        self.worker.signals.task_finished.connect(self.on_task_finished)
        self.worker.signals.error_occurred.connect(self.on_error)

        self.init_ui()
        self.setup_logging()

    def init_ui(self):
        # 根容器
        root = QtWidgets.QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)

        main_layout = QtWidgets.QVBoxLayout(root)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(20)

        # ---------------- 上半部分：功能控制区 ----------------
        top_container = QtWidgets.QWidget()
        top_layout = QtWidgets.QHBoxLayout(top_container)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(24)

        # === 左卡片：账号接入 ===
        card_login = QtWidgets.QFrame()
        card_login.setObjectName("Card")
        # 增加阴影效果 (QGraphicsEffect 只能在 Python 端加，样式表不支持复杂阴影)
        shadow_login = QtWidgets.QGraphicsDropShadowEffect(self)
        shadow_login.setBlurRadius(15)
        shadow_login.setColor(QtGui.QColor(0, 0, 0, 20))
        shadow_login.setOffset(0, 4)
        card_login.setGraphicsEffect(shadow_login)

        login_layout = QtWidgets.QVBoxLayout(card_login)
        login_layout.setContentsMargins(24, 24, 24, 24)
        login_layout.setSpacing(16)

        lbl_login_title = QtWidgets.QLabel("账号控制台")
        lbl_login_title.setObjectName("CardTitle")
        login_layout.addWidget(lbl_login_title)

        # 二维码区域
        self.lbl_qr = QtWidgets.QLabel("点击启动以开始")
        self.lbl_qr.setObjectName("QrPlaceholder")
        self.lbl_qr.setAlignment(QtCore.Qt.AlignCenter)
        self.lbl_qr.setFixedSize(220, 220)

        qr_wrapper = QtWidgets.QHBoxLayout()
        qr_wrapper.addStretch()
        qr_wrapper.addWidget(self.lbl_qr)
        qr_wrapper.addStretch()
        login_layout.addLayout(qr_wrapper)

        # 状态文本
        self.lbl_status = QtWidgets.QLabel("当前状态：未连接")
        self.lbl_status.setObjectName("StatusLabel")
        self.lbl_status.setAlignment(QtCore.Qt.AlignCenter)
        login_layout.addWidget(self.lbl_status)

        # 登录/退出按钮组
        login_btn_layout = QtWidgets.QHBoxLayout()
        self.btn_login = QtWidgets.QPushButton("启动浏览器 & 登录")
        self.btn_login.setObjectName("PrimaryBtn")
        self.btn_login.clicked.connect(self.start_login)
        self.btn_login.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_login.setMinimumHeight(38)

        self.btn_logout = QtWidgets.QPushButton("退出")
        self.btn_logout.setObjectName("DangerBtn")
        self.btn_logout.setEnabled(False)
        self.btn_logout.clicked.connect(self.start_logout)
        self.btn_logout.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_logout.setMinimumHeight(38)

        login_btn_layout.addWidget(self.btn_login, 3)
        login_btn_layout.addWidget(self.btn_logout, 1)
        login_layout.addLayout(login_btn_layout)

        login_layout.addStretch()  # 撑满

        # === 右卡片：任务控制 ===
        card_task = QtWidgets.QFrame()
        card_task.setObjectName("Card")
        shadow_task = QtWidgets.QGraphicsDropShadowEffect(self)
        shadow_task.setBlurRadius(15)
        shadow_task.setColor(QtGui.QColor(0, 0, 0, 20))
        shadow_task.setOffset(0, 4)
        card_task.setGraphicsEffect(shadow_task)

        task_layout = QtWidgets.QVBoxLayout(card_task)
        task_layout.setContentsMargins(24, 24, 24, 24)
        task_layout.setSpacing(16)

        lbl_task_title = QtWidgets.QLabel("任务配置")
        lbl_task_title.setObjectName("CardTitle")
        task_layout.addWidget(lbl_task_title)

        # 选项卡控件
        self.tabs = QtWidgets.QTabWidget()

        # Tab 1: 打招呼
        tab_greet = QtWidgets.QWidget()
        layout_greet = QtWidgets.QVBoxLayout(tab_greet)
        layout_greet.setContentsMargins(20, 30, 20, 20)
        layout_greet.setSpacing(15)

        form_greet = QtWidgets.QHBoxLayout()
        lbl_g = QtWidgets.QLabel("设定目标人数：")
        lbl_g.setStyleSheet("font-weight: bold; color: #4b5563;")
        self.spin_greet_count = QtWidgets.QSpinBox()
        self.spin_greet_count.setRange(1, 500)
        self.spin_greet_count.setValue(5)
        self.spin_greet_count.setFixedWidth(120)
        self.spin_greet_count.setSuffix(" 人")
        form_greet.addWidget(lbl_g)
        form_greet.addWidget(self.spin_greet_count)
        form_greet.addStretch()

        desc_greet = QtWidgets.QLabel(
            "功能说明：\n1. 自动筛选符合关键词且在线的牛人。\n2. 点击名片进入详情页并打招呼。\n3. 若遇到每日上限，自动停止任务。")
        desc_greet.setStyleSheet(
            "color: #6b7280; font-size: 12px; line-height: 1.5; background: #f9fafb; padding: 10px; border-radius: 6px;")
        desc_greet.setWordWrap(True)

        layout_greet.addLayout(form_greet)
        layout_greet.addWidget(desc_greet)
        layout_greet.addStretch()
        self.tabs.addTab(tab_greet, " 👋 自动打招呼")

        # Tab 2: 刷浏览量
        tab_browse = QtWidgets.QWidget()
        layout_browse = QtWidgets.QVBoxLayout(tab_browse)
        layout_browse.setContentsMargins(20, 30, 20, 20)
        layout_browse.setSpacing(15)

        form_browse = QtWidgets.QHBoxLayout()
        lbl_b = QtWidgets.QLabel("设定运行时长：")
        lbl_b.setStyleSheet("font-weight: bold; color: #4b5563;")
        self.spin_browse_time = QtWidgets.QSpinBox()
        self.spin_browse_time.setRange(1, 1440)
        self.spin_browse_time.setValue(20)
        self.spin_browse_time.setSuffix(" 分钟")
        self.spin_browse_time.setFixedWidth(120)
        form_browse.addWidget(lbl_b)
        form_browse.addWidget(self.spin_browse_time)
        form_browse.addStretch()

        desc_browse = QtWidgets.QLabel(
            "功能说明：\n1. 打开第一个牛人详情页。\n2. 持续自动翻页 (按右键)，模拟活跃状态。\n3. 不进行沟通，仅增加账号浏览活跃度。")
        desc_browse.setStyleSheet(
            "color: #6b7280; font-size: 12px; line-height: 1.5; background: #f9fafb; padding: 10px; border-radius: 6px;")
        desc_browse.setWordWrap(True)

        layout_browse.addLayout(form_browse)
        layout_browse.addWidget(desc_browse)
        layout_browse.addStretch()
        self.tabs.addTab(tab_browse, " 👁️ 刷浏览量")

        task_layout.addWidget(self.tabs)

        # 任务操作按钮
        action_layout = QtWidgets.QHBoxLayout()
        self.btn_start = QtWidgets.QPushButton("开始执行")
        self.btn_start.setObjectName("PrimaryBtn")
        self.btn_start.setEnabled(False)
        self.btn_start.clicked.connect(self.start_task)
        self.btn_start.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_start.setMinimumHeight(42)

        self.btn_stop = QtWidgets.QPushButton("停止")
        self.btn_stop.setObjectName("DangerBtn")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_task)
        self.btn_stop.setCursor(QtCore.Qt.PointingHandCursor)
        self.btn_stop.setMinimumHeight(42)

        action_layout.addWidget(self.btn_start, 3)
        action_layout.addWidget(self.btn_stop, 1)
        task_layout.addLayout(action_layout)

        # 添加到顶部布局
        top_layout.addWidget(card_login, 2)
        top_layout.addWidget(card_task, 3)

        # ---------------- 下半部分：日志区 (Splitter) ----------------

        # 日志容器
        log_container = QtWidgets.QFrame()
        log_container.setObjectName("Card")
        # 阴影
        shadow_log = QtWidgets.QGraphicsDropShadowEffect(self)
        shadow_log.setBlurRadius(15)
        shadow_log.setColor(QtGui.QColor(0, 0, 0, 15))
        shadow_log.setOffset(0, 4)
        log_container.setGraphicsEffect(shadow_log)

        log_layout = QtWidgets.QVBoxLayout(log_container)
        log_layout.setContentsMargins(0, 0, 0, 0)
        log_layout.setSpacing(0)

        # 日志标题栏
        log_header = QtWidgets.QLabel(" 运行日志 / Operation Logs")
        log_header.setFixedHeight(36)
        log_header.setStyleSheet("""
            background-color: #f9fafb; 
            border-bottom: 1px solid #e4e7ed; 
            border-radius: 12px 12px 0 0;
            padding-left: 16px;
            font-weight: 600;
            color: #4b5563;
            font-size: 12px;
        """)
        log_layout.addWidget(log_header)

        # 日志文本框
        self.txt_log = QtWidgets.QPlainTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setFrameShape(QtWidgets.QFrame.NoFrame)
        log_layout.addWidget(self.txt_log)

        # 使用 Splitter
        splitter = QtWidgets.QSplitter(Qt.Vertical)
        splitter.addWidget(top_container)
        splitter.addWidget(log_container)

        # 初始高度比例 2:1
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)

        # Splitter Handle 隐形处理，增加间距感
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: transparent;
                height: 16px;
            }
        """)

        main_layout.addWidget(splitter)

    def setup_logging(self):
        handler = QPlainTextEditLogger(self.txt_log)
        # 日志格式优化
        handler.setFormatter(logging.Formatter('[%(asctime)s] %(message)s', "%H:%M:%S"))
        logger = logging.getLogger('core.boos_driver')
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)
        logging.getLogger().addHandler(handler)

    @Slot(str)
    def append_log(self, text):
        self.txt_log.appendPlainText(text)

    @Slot(str)
    def update_status_label(self, text):
        self.lbl_status.setText(f"当前状态：{text}")

    @Slot(str)
    def display_qr_code(self, url):
        self.txt_log.appendPlainText(">> 二维码已加载，请扫码...")
        self.lbl_status.setText("当前状态：等待扫码")
        try:
            response = requests.get(url)
            response.raise_for_status()
            image = QtGui.QImage()
            image.loadFromData(response.content)
            pixmap = QtGui.QPixmap.fromImage(image)
            self.lbl_qr.setPixmap(pixmap.scaled(200, 200, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
        except:
            self.lbl_qr.setText("二维码加载失败")

    def start_login(self):
        self.btn_login.setEnabled(False)
        self.btn_logout.setEnabled(False)
        self.lbl_qr.setText("初始化中...")
        self.lbl_status.setText("当前状态：启动浏览器...")
        self.worker.action = 'login'
        self.worker.start()

    def on_login_success(self):
        self.lbl_qr.setText("已登录")
        # 登录成功的绿色边框样式
        self.lbl_qr.setStyleSheet("""
            QLabel#QrPlaceholder {
                border: 2px solid #34d399;
                color: #34d399;
                font-weight: bold;
                font-size: 16px;
                background-color: #ecfdf5;
            }
        """)
        self.lbl_status.setText("当前状态：在线 (已就绪)")
        self.btn_login.setText("已连接")
        self.btn_logout.setEnabled(True)
        self.btn_start.setEnabled(True)
        self.txt_log.appendPlainText(">> 系统就绪，请在右侧选择任务并开始。")

    def start_logout(self):
        reply = QtWidgets.QMessageBox.question(
            self, '确认操作', "确定要清除 Cookie 并关闭浏览器吗？",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No
        )
        if reply == QtWidgets.QMessageBox.Yes:
            self.btn_logout.setEnabled(False)
            self.btn_start.setEnabled(False)
            self.worker.action = 'logout'
            self.worker.start()

    def on_logout_success(self):
        self.lbl_qr.clear()
        self.lbl_qr.setText("未连接")
        # 恢复默认灰色样式
        self.lbl_qr.setStyleSheet("""
            QLabel#QrPlaceholder {
                background-color: #f9fafb;
                border: 2px dashed #dcdfe6;
                color: #c0c4cc;
            }
        """)
        self.lbl_status.setText("当前状态：已断开")
        self.btn_login.setText("启动浏览器 & 登录")
        self.btn_login.setEnabled(True)
        self.btn_logout.setEnabled(False)
        self.btn_start.setEnabled(False)

    def start_task(self):
        idx = self.tabs.currentIndex()
        if idx == 0:
            val = self.spin_greet_count.value()
            self.worker.action = 'greet'
            self.worker.params = {'count': val}
            self.txt_log.appendPlainText(f"\n-------- [任务启动] 自动打招呼 (目标 {val} 人) --------")
        else:
            val = self.spin_browse_time.value()
            self.worker.action = 'browse'
            self.worker.params = {'minutes': val}
            self.txt_log.appendPlainText(f"\n-------- [任务启动] 刷浏览量 (限时 {val} 分钟) --------")

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_logout.setEnabled(False)
        self.lbl_status.setText("当前状态：任务运行中...")
        self.worker.start()

    def stop_task(self):
        self.txt_log.appendPlainText(">> 正在请求停止...")
        self.worker.stop_current_task()
        self.btn_stop.setEnabled(False)

    def on_task_finished(self):
        self.txt_log.appendPlainText("-------- [系统] 任务已结束 --------")
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_logout.setEnabled(True)
        self.lbl_status.setText("当前状态：在线 (空闲)")

    def on_error(self, msg):
        self.txt_log.appendPlainText(f"[错误] {msg}")
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_login.setEnabled(True)
        self.lbl_status.setText("当前状态：发生错误")


if __name__ == "__main__":
    # --- 1. 修复 Windows 任务栏图标显示 (让系统认为这是个独立程序) ---
    import ctypes

    if sys.platform == 'win32':
        try:
            # 任意唯一的字符串 ID
            myappid = 'boos.auto.helper.pro.v1'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception as e:
            print(f"设置任务栏图标失败: {e}")

    app = QtWidgets.QApplication(sys.argv)

    # --- 2. 设置全局应用图标 ---
    # 假设你的图片名叫 logo.png，如果放在子文件夹要写 "assets/logo.png"
    icon_path = resource_path("media/windown_icon.ico")
    app.setWindowIcon(QtGui.QIcon(icon_path))


    if os.path.exists(icon_path):
        app.setWindowIcon(QtGui.QIcon(icon_path))
    else:
        # 如果找不到图片，打印个提示（仅调试用）
        print(f"提示: 未找到图标文件 '{icon_path}'，将使用默认图标。")

    # 设置全局字体
    font = QtGui.QFont("Segoe UI", 10)
    font.setStyleStrategy(QtGui.QFont.PreferAntialias)
    app.setFont(font)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
