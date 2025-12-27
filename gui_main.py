import sys
import logging
import requests
import time
import os
import threading
from io import BytesIO

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Signal, Slot, QThread, QObject

# 导入原有的驱动类
from core.boos_driver import BoosDriver
from core import selectors
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- 日志重定向 ---
class LogSignal(QObject):
    """用于发送日志的信号类"""
    append_log = Signal(str)

class QPlainTextEditLogger(logging.Handler):
    """将日志输出重定向到 GUI 的文本框"""
    def __init__(self, widget):
        super().__init__()
        self.widget = widget
        # 创建一个 QObject 来持有信号
        self.signal_emitter = LogSignal()
        # 将信号连接到文本框的 appendPlainText 槽函数
        self.signal_emitter.append_log.connect(self.widget.appendPlainText)

    def emit(self, record):
        try:
            msg = self.format(record)
            # 通过信号发送日志，自动处理线程安全
            self.signal_emitter.append_log.emit(msg)
        except Exception:
            pass

# --- 信号类 ---
class WorkerSignals(QObject):
    log_message = Signal(str)
    update_status = Signal(str) # 更新状态标签
    qr_code_url = Signal(str)
    login_success = Signal()
    logout_success = Signal()   # 新增：退出登录成功信号
    task_finished = Signal()
    error_occurred = Signal(str)

# --- 修改后的驱动类 ---
class GuiBoosDriver(BoosDriver):
    """继承原 BoosDriver，拦截关键信息发送给 GUI"""
    def __init__(self, signals, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.signals = signals
        self._stop_flag = False

    def _get_qrcode(self):
        """重写获取二维码方法，发送 URL 给 GUI"""
        self.logger.info("正在获取二维码...")
        try:
            wait = WebDriverWait(self.driver, 20)
            qr_code = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, selectors.QRCODE_IMG_CSS)))
            # 等待图片渲染
            wait.until(lambda driver: qr_code.size["width"] > 0)

            url = qr_code.get_attribute("src")
            self.logger.info(f"获取到二维码 URL")
            self.signals.qr_code_url.emit(url)
        except Exception as e:
            self.logger.error(f"获取二维码失败: {str(e)}")

    def _run_browse_loop(self, max_minutes: int = 20):
        """重写刷浏览量循环，支持停止标志"""
        self.logger.info(f"准备进入刷浏览量模式，限时 {max_minutes} 分钟...")

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
        """重写打招呼循环，支持停止标志"""
        self.logger.info(f"开始执行自动打招呼，目标人数：{target_count}")
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
                    except: pass

                    if has_kw and is_online:
                        target_card = card
                        target_id = gid
                        self.logger.info(f"找到匹配牛人: {text.replace(chr(10), ' ')[:20]}...")
                        break
                except: continue

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

# --- 工作线程 ---
class WorkerThread(QThread):
    def __init__(self):
        super().__init__()
        self.signals = WorkerSignals()
        self.driver = None
        self.action = None # 'login', 'greet', 'browse', 'logout'
        self.params = {}

    def run(self):
        try:
            # 初始化 Driver (如果还没初始化且不是退出操作)
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
                self.signals.log_message.emit(f"检测到 {applied} 个本地 Cookie，尝试自动登录...")
                self.signals.update_status.emit("正在验证 Cookie...")

                self.driver.driver.refresh()
                self.driver._click_login_if_present(3)

                if self.driver._has_recommend_talents_menu(timeout_seconds=5):
                    self.signals.log_message.emit("Cookie 验证成功，无需扫码！")
                    self.driver._persist_cookies()
                    self.driver._click_recommend_talents()
                    self.signals.login_success.emit()
                    return
                else:
                    self.signals.log_message.emit("Cookie 已失效，切换到扫码登录...")
            else:
                self.signals.log_message.emit("未检测到本地 Cookie，准备扫码登录...")

            self.signals.update_status.emit("等待获取二维码...")
            self.driver._close_download_popup_if_present(2)
            self.driver._click_login_if_present(2)
            self.driver._click_app_scan_login()
            self.driver._get_qrcode()

            self.driver._wait_for_scan_login()

            self.driver._persist_cookies()
            self.driver._close_download_popup_if_present(2)
            self.driver._click_recommend_talents()

            self.signals.log_message.emit("扫码登录成功！")
            self.signals.login_success.emit()

        except Exception as e:
            raise e

    def _do_logout(self):
        """执行退出登录逻辑"""
        self.signals.update_status.emit("正在退出登录...")

        # 1. 删除本地 Cookie 文件
        cookie_file = "cookies.json"
        if os.path.exists(cookie_file):
            try:
                os.remove(cookie_file)
                self.signals.log_message.emit(f"已删除本地文件: {cookie_file}")
            except Exception as e:
                self.signals.log_message.emit(f"删除 Cookie 文件失败: {e}")
        else:
            self.signals.log_message.emit("本地 Cookie 文件不存在")

        # 2. 关闭浏览器
        if self.driver:
            self.signals.log_message.emit("正在关闭浏览器...")
            try:
                self.driver.close() # 这会调用 driver.quit()
            except Exception as e:
                self.signals.log_message.emit(f"关闭浏览器时出错(可忽略): {e}")
            self.driver = None # 重置 driver 对象

        self.signals.logout_success.emit()

    def stop_current_task(self):
        if self.driver:
            self.driver.stop_task()

# --- 主窗口 ---
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Boss直聘 自动助手")
        self.resize(900, 650)
        self.setStyleSheet(self._get_style())

        # 初始化后台线程
        self.worker = WorkerThread()
        self.worker.signals.qr_code_url.connect(self.display_qr_code)
        self.worker.signals.log_message.connect(self.append_log)
        self.worker.signals.update_status.connect(self.update_qr_label)
        self.worker.signals.login_success.connect(self.on_login_success)
        self.worker.signals.logout_success.connect(self.on_logout_success) # 连接退出信号
        self.worker.signals.task_finished.connect(self.on_task_finished)
        self.worker.signals.error_occurred.connect(self.on_error)

        self.init_ui()
        self.setup_logging()

    def _get_style(self):
        return """
            QMainWindow { background-color: #f0f2f5; }
            QGroupBox { font-weight: bold; border: 1px solid #dcdcdc; border-radius: 5px; margin-top: 10px; background: white; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; }
            QPushButton { background-color: #00bebd; color: white; border-radius: 4px; padding: 8px; font-weight: bold; }
            QPushButton:hover { background-color: #00a9a8; }
            QPushButton:disabled { background-color: #cccccc; }
            QTextEdit { background-color: #1e1e1e; color: #00ff00; font-family: Consolas; font-size: 12px; }
            QLabel#QrLabel { border: 2px dashed #cccccc; background-color: #f9f9f9; color: #555; font-weight: bold;}
        """

    def init_ui(self):
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QtWidgets.QHBoxLayout(central_widget)

        # === 左侧面板：控制区 ===
        left_panel = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_panel)
        left_panel.setFixedWidth(350)

        # 1. 登录模块
        grp_login = QtWidgets.QGroupBox("1. 初始化")
        login_layout = QtWidgets.QVBoxLayout()

        # 按钮行
        btn_row = QtWidgets.QHBoxLayout()
        self.btn_login = QtWidgets.QPushButton("启动浏览器 & 登录")
        self.btn_login.clicked.connect(self.start_login)

        self.btn_logout = QtWidgets.QPushButton("退出登录")
        self.btn_logout.setStyleSheet("background-color: #ff4d4f;") # 红色按钮
        self.btn_logout.setEnabled(False) # 初始禁用
        self.btn_logout.clicked.connect(self.start_logout)

        btn_row.addWidget(self.btn_login)
        btn_row.addWidget(self.btn_logout)
        login_layout.addLayout(btn_row)

        grp_login.setLayout(login_layout)

        # 2. 二维码/状态显示区
        self.lbl_qr = QtWidgets.QLabel("未运行")
        self.lbl_qr.setObjectName("QrLabel")
        self.lbl_qr.setAlignment(QtCore.Qt.AlignCenter)
        self.lbl_qr.setFixedSize(200, 200)
        qr_container = QtWidgets.QHBoxLayout()
        qr_container.addStretch()
        qr_container.addWidget(self.lbl_qr)
        qr_container.addStretch()
        login_layout.addLayout(qr_container)

        # 3. 任务控制模块
        self.grp_task = QtWidgets.QGroupBox("2. 任务执行")
        self.grp_task.setEnabled(False)
        task_layout = QtWidgets.QVBoxLayout()

        self.tabs = QtWidgets.QTabWidget()

        # Tab 1
        tab_greet = QtWidgets.QWidget()
        form_greet = QtWidgets.QFormLayout(tab_greet)
        self.spin_greet_count = QtWidgets.QSpinBox()
        self.spin_greet_count.setRange(1, 200)
        self.spin_greet_count.setValue(5)
        form_greet.addRow("打招呼人数:", self.spin_greet_count)
        self.tabs.addTab(tab_greet, "自动打招呼")

        # Tab 2
        tab_browse = QtWidgets.QWidget()
        form_browse = QtWidgets.QFormLayout(tab_browse)
        self.spin_browse_time = QtWidgets.QSpinBox()
        self.spin_browse_time.setRange(1, 1440)
        self.spin_browse_time.setValue(20)
        self.spin_browse_time.setSuffix(" 分钟")
        form_browse.addRow("运行时长:", self.spin_browse_time)
        self.tabs.addTab(tab_browse, "刷浏览量")

        task_layout.addWidget(self.tabs)

        self.lbl_status = QtWidgets.QLabel("请先登录，并在浏览器中手动选好城市/职位。")
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setStyleSheet("color: #666; font-size: 11px;")
        task_layout.addWidget(self.lbl_status)

        btn_layout = QtWidgets.QHBoxLayout()
        self.btn_start = QtWidgets.QPushButton("开始任务")
        self.btn_start.clicked.connect(self.start_task)
        self.btn_stop = QtWidgets.QPushButton("停止")
        self.btn_stop.setStyleSheet("background-color: #ff4d4f;")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_task)

        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_stop)
        task_layout.addLayout(btn_layout)

        self.grp_task.setLayout(task_layout)

        left_layout.addWidget(grp_login)
        left_layout.addWidget(self.grp_task)
        left_layout.addStretch()

        # === 右侧面板：日志 ===
        right_panel = QtWidgets.QGroupBox("运行日志")
        right_layout = QtWidgets.QVBoxLayout(right_panel)
        self.txt_log = QtWidgets.QPlainTextEdit()
        self.txt_log.setReadOnly(True)
        right_layout.addWidget(self.txt_log)

        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel, 1)

    def setup_logging(self):
        handler = QPlainTextEditLogger(self.txt_log)
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger = logging.getLogger('core.boos_driver')
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)
        logging.getLogger().addHandler(handler)

    @Slot(str)
    def append_log(self, text):
        self.txt_log.appendPlainText(text)

    @Slot(str)
    def update_qr_label(self, text):
        self.lbl_qr.clear()
        self.lbl_qr.setText(text)

    @Slot(str)
    def display_qr_code(self, url):
        self.txt_log.appendPlainText(f"收到二维码 URL，请扫码...")
        try:
            response = requests.get(url)
            response.raise_for_status()
            image = QtGui.QImage()
            image.loadFromData(response.content)
            pixmap = QtGui.QPixmap.fromImage(image)
            self.lbl_qr.setPixmap(pixmap.scaled(200, 200, QtCore.Qt.KeepAspectRatio))
        except Exception as e:
            self.txt_log.appendPlainText(f"二维码加载失败: {e}")
            self.lbl_qr.setText("二维码加载失败")

    def start_login(self):
        self.btn_login.setEnabled(False)
        self.btn_logout.setEnabled(False)
        self.txt_log.appendPlainText(">>> 正在启动浏览器...")
        self.lbl_qr.setText("正在初始化...")
        self.worker.action = 'login'
        self.worker.start()

    def on_login_success(self):
        self.txt_log.appendPlainText(">>> 登录成功！")
        self.lbl_qr.setText("已登录")
        self.grp_task.setEnabled(True)
        self.btn_login.setText("已登录")
        self.btn_login.setEnabled(False) # 登录成功后禁用登录按钮
        self.btn_logout.setEnabled(True) # 启用退出按钮
        self.lbl_status.setText("状态：已就绪。请在浏览器中确认 城市/职位 筛选已设置好。")

    def start_logout(self):
        # 确认对话框
        reply = QtWidgets.QMessageBox.question(
            self, '确认退出', "确定要清除 Cookie 并关闭浏览器吗？",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No
        )
        if reply == QtWidgets.QMessageBox.Yes:
            self.txt_log.appendPlainText(">>> 正在退出登录...")
            self.btn_logout.setEnabled(False)
            self.worker.action = 'logout'
            self.worker.start()

    def on_logout_success(self):
        self.txt_log.appendPlainText(">>> 已退出登录，资源已释放。")
        self.lbl_qr.setText("未运行")
        self.lbl_qr.clear()

        # 重置界面状态
        self.btn_login.setEnabled(True)
        self.btn_login.setText("启动浏览器 & 登录")
        self.btn_logout.setEnabled(False)

        self.grp_task.setTitle("2. 任务执行")
        self.grp_task.setEnabled(False)
        self.lbl_status.setText("请先登录，并在浏览器中手动选好城市/职位。")

    def start_task(self):
        idx = self.tabs.currentIndex()
        if idx == 0:
            count = self.spin_greet_count.value()
            self.worker.action = 'greet'
            self.worker.params = {'count': count}
            self.txt_log.appendPlainText(f">>> 启动任务：自动打招呼 ({count}人)")
        else:
            mins = self.spin_browse_time.value()
            self.worker.action = 'browse'
            self.worker.params = {'minutes': mins}
            self.txt_log.appendPlainText(f">>> 启动任务：刷浏览量 ({mins}分钟)")

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_logout.setEnabled(False) # 任务运行中禁止退出登录
        self.grp_task.setTitle("2. 任务执行 (运行中...)")
        self.worker.start()

    def stop_task(self):
        self.txt_log.appendPlainText(">>> 正在请求停止任务...")
        self.worker.stop_current_task()
        self.btn_stop.setEnabled(False)

    def on_task_finished(self):
        self.txt_log.appendPlainText(">>> 任务结束")
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_logout.setEnabled(True) # 恢复退出按钮
        self.grp_task.setTitle("2. 任务执行")

    def on_error(self, msg):
        self.txt_log.appendPlainText(f"ERROR: {msg}")
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_login.setEnabled(True)
        self.btn_logout.setEnabled(False) # 出错时禁用退出，允许重新登录
        self.lbl_qr.setText("发生错误")

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())