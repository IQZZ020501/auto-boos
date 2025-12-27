from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime

from PySide6 import QtCore, QtGui, QtWidgets


APP_TITLE = "Boos Auto · PySide6 Demo"


def _qcolor(hex_color: str) -> QtGui.QColor:
    return QtGui.QColor(hex_color)


def app_stylesheet() -> str:
    # 注意：尽量避免依赖系统字体名，使用 Qt 默认字体即可。
    return """
    * { 
        font-size: 13px;
    }

    QMainWindow {
        background: #0b1220;
    }

    QWidget#Root {
        background: #0b1220;
    }

    /* Sidebar */
    QWidget#Sidebar {
        background: #0f1a2f;
        border-right: 1px solid rgba(255,255,255,0.08);
    }

    QLabel#Brand {
        color: rgba(255,255,255,0.92);
        font-size: 14px;
        font-weight: 600;
        padding: 10px 12px;
    }

    QPushButton#NavButton {
        text-align: left;
        padding: 10px 12px;
        border-radius: 10px;
        color: rgba(255,255,255,0.86);
        background: transparent;
    }
    QPushButton#NavButton:hover {
        background: rgba(255,255,255,0.06);
    }
    QPushButton#NavButton:checked {
        background: rgba(59, 130, 246, 0.22);
        border: 1px solid rgba(59, 130, 246, 0.35);
        color: rgba(255,255,255,0.95);
    }

    /* Top bar */
    QWidget#Topbar {
        background: rgba(255,255,255,0.02);
        border-bottom: 1px solid rgba(255,255,255,0.06);
    }

    QLineEdit#Search {
        padding: 10px 12px;
        border-radius: 12px;
        border: 1px solid rgba(255,255,255,0.08);
        background: rgba(255,255,255,0.04);
        color: rgba(255,255,255,0.92);
        selection-background-color: rgba(59,130,246,0.55);
    }
    QLineEdit#Search:focus {
        border: 1px solid rgba(59, 130, 246, 0.55);
        background: rgba(255,255,255,0.06);
    }

    QPushButton#Action {
        padding: 10px 12px;
        border-radius: 12px;
        border: 1px solid rgba(255,255,255,0.10);
        background: rgba(255,255,255,0.04);
        color: rgba(255,255,255,0.92);
    }
    QPushButton#Action:hover {
        background: rgba(255,255,255,0.07);
    }
    QPushButton#Action:pressed {
        background: rgba(255,255,255,0.10);
    }

    /* Cards */
    QFrame#Card {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px;
    }

    QLabel#CardTitle {
        color: rgba(255,255,255,0.70);
        font-size: 12px;
    }

    QLabel#CardValue {
        color: rgba(255,255,255,0.95);
        font-size: 22px;
        font-weight: 700;
    }

    QLabel#Muted {
        color: rgba(255,255,255,0.62);
    }

    /* Group panel */
    QFrame#Panel {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 16px;
    }

    QLabel#PanelTitle {
        color: rgba(255,255,255,0.92);
        font-weight: 600;
        font-size: 14px;
    }

    /* Table */
    QTableWidget {
        background: transparent;
        color: rgba(255,255,255,0.92);
        gridline-color: rgba(255,255,255,0.08);
        border: none;
        selection-background-color: rgba(59,130,246,0.28);
        selection-color: rgba(255,255,255,0.95);
    }

    QHeaderView::section {
        background: rgba(255,255,255,0.03);
        color: rgba(255,255,255,0.68);
        border: none;
        padding: 10px 10px;
    }

    QTableWidget::item {
        padding: 10px 10px;
    }

    QTableWidget::item:selected {
        border: 1px solid rgba(59,130,246,0.45);
    }

    /* Inputs */
    QLineEdit, QComboBox {
        padding: 9px 10px;
        border-radius: 12px;
        border: 1px solid rgba(255,255,255,0.10);
        background: rgba(255,255,255,0.04);
        color: rgba(255,255,255,0.92);
    }

    QLineEdit:focus, QComboBox:focus {
        border: 1px solid rgba(59,130,246,0.55);
        background: rgba(255,255,255,0.06);
    }

    QComboBox::drop-down {
        border: none;
        width: 28px;
    }

    /* Buttons */
    QPushButton#Primary {
        padding: 10px 12px;
        border-radius: 12px;
        background: rgba(59,130,246,0.90);
        border: 1px solid rgba(59,130,246,0.55);
        color: #ffffff;
        font-weight: 600;
    }
    QPushButton#Primary:hover {
        background: rgba(59,130,246,1.0);
    }
    QPushButton#Primary:pressed {
        background: rgba(37,99,235,1.0);
    }

    QPushButton#Danger {
        padding: 10px 12px;
        border-radius: 12px;
        background: rgba(239,68,68,0.85);
        border: 1px solid rgba(239,68,68,0.55);
        color: #ffffff;
        font-weight: 600;
    }
    QPushButton#Danger:hover {
        background: rgba(239,68,68,0.95);
    }

    QStatusBar {
        background: rgba(255,255,255,0.02);
        color: rgba(255,255,255,0.72);
        border-top: 1px solid rgba(255,255,255,0.06);
    }

    /* Scrollbars */
    QScrollBar:vertical {
        width: 12px;
        background: transparent;
        margin: 8px 2px 8px 2px;
    }
    QScrollBar::handle:vertical {
        background: rgba(255,255,255,0.10);
        border-radius: 6px;
        min-height: 24px;
    }
    QScrollBar::handle:vertical:hover {
        background: rgba(255,255,255,0.16);
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
    """


@dataclass(frozen=True)
class DemoRow:
    created_at: str
    task: str
    status: str
    duration_ms: int


class Toast(QtWidgets.QFrame):
    def __init__(self, text: str, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Toast")
        self.setWindowFlags(
            QtCore.Qt.WindowType.FramelessWindowHint
            | QtCore.Qt.WindowType.Tool
            | QtCore.Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)

        root = QtWidgets.QFrame()
        root.setObjectName("ToastBody")
        root.setStyleSheet(
            """
            QFrame#ToastBody {
                background: rgba(17, 24, 39, 0.92);
                border: 1px solid rgba(255,255,255,0.10);
                border-radius: 14px;
            }
            QLabel {
                color: rgba(255,255,255,0.92);
            }
            """
        )

        label = QtWidgets.QLabel(text)
        label.setWordWrap(True)
        label.setContentsMargins(14, 12, 14, 12)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(root)

        inner = QtWidgets.QVBoxLayout(root)
        inner.setContentsMargins(0, 0, 0, 0)
        inner.addWidget(label)

        self._timer = QtCore.QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.close)

    def show_for(self, ms: int = 1700) -> None:
        self._timer.start(ms)
        self.show()


class DemoWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(1100, 720)

        root = QtWidgets.QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)

        outer = QtWidgets.QHBoxLayout(root)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(12)

        # 先创建 stack：侧边栏按钮需要绑定到它
        self.stack = QtWidgets.QStackedWidget()

        self.sidebar = self._build_sidebar()
        outer.addWidget(self.sidebar)

        content = QtWidgets.QWidget()
        content_layout = QtWidgets.QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)

        self.topbar = self._build_topbar()
        content_layout.addWidget(self.topbar)

        self.stack.addWidget(self._build_dashboard_page())
        self.stack.addWidget(self._build_tasks_page())
        self.stack.addWidget(self._build_settings_page())
        content_layout.addWidget(self.stack, 1)

        outer.addWidget(content, 1)

        self.status = QtWidgets.QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("就绪")

        self._seed_data()

    def _build_sidebar(self) -> QtWidgets.QWidget:
        side = QtWidgets.QWidget()
        side.setObjectName("Sidebar")
        side.setFixedWidth(230)

        layout = QtWidgets.QVBoxLayout(side)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        brand = QtWidgets.QLabel("Boos Auto")
        brand.setObjectName("Brand")
        layout.addWidget(brand)

        layout.addSpacing(4)

        self.nav_dashboard = self._nav_button("仪表盘", checked=True)
        self.nav_tasks = self._nav_button("任务", checked=False)
        self.nav_settings = self._nav_button("设置", checked=False)

        group = QtWidgets.QButtonGroup(self)
        group.setExclusive(True)
        group.addButton(self.nav_dashboard, 0)
        group.addButton(self.nav_tasks, 1)
        group.addButton(self.nav_settings, 2)
        group.idClicked.connect(self.stack.setCurrentIndex)

        layout.addWidget(self.nav_dashboard)
        layout.addWidget(self.nav_tasks)
        layout.addWidget(self.nav_settings)

        layout.addStretch(1)

        footer = QtWidgets.QLabel("PySide6 · Demo")
        footer.setObjectName("Muted")
        footer.setContentsMargins(4, 6, 4, 2)
        layout.addWidget(footer)

        return side

    def _nav_button(self, text: str, checked: bool) -> QtWidgets.QPushButton:
        btn = QtWidgets.QPushButton(text)
        btn.setObjectName("NavButton")
        btn.setCheckable(True)
        btn.setChecked(checked)
        return btn

    def _build_topbar(self) -> QtWidgets.QWidget:
        top = QtWidgets.QWidget()
        top.setObjectName("Topbar")

        layout = QtWidgets.QHBoxLayout(top)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        self.search = QtWidgets.QLineEdit()
        self.search.setObjectName("Search")
        self.search.setPlaceholderText("搜索任务、公司、关键词…")
        self.search.returnPressed.connect(self._on_search)

        btn_run = QtWidgets.QPushButton("运行示例")
        btn_run.setObjectName("Action")
        btn_run.clicked.connect(self._simulate_run)

        btn_toast = QtWidgets.QPushButton("提示")
        btn_toast.setObjectName("Action")
        btn_toast.clicked.connect(lambda: self._toast("已保存设置（示例）"))

        layout.addWidget(self.search, 1)
        layout.addWidget(btn_run)
        layout.addWidget(btn_toast)

        return top

    def _card(self, title: str, value: str, hint: str) -> QtWidgets.QFrame:
        card = QtWidgets.QFrame()
        card.setObjectName("Card")
        layout = QtWidgets.QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(6)

        t = QtWidgets.QLabel(title)
        t.setObjectName("CardTitle")

        v = QtWidgets.QLabel(value)
        v.setObjectName("CardValue")

        h = QtWidgets.QLabel(hint)
        h.setObjectName("Muted")

        layout.addWidget(t)
        layout.addWidget(v)
        layout.addWidget(h)
        return card

    def _panel(self, title: str) -> tuple[QtWidgets.QFrame, QtWidgets.QVBoxLayout]:
        panel = QtWidgets.QFrame()
        panel.setObjectName("Panel")
        layout = QtWidgets.QVBoxLayout(panel)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        header = QtWidgets.QLabel(title)
        header.setObjectName("PanelTitle")
        layout.addWidget(header)

        return panel, layout

    def _build_dashboard_page(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        cards_row = QtWidgets.QHBoxLayout()
        cards_row.setSpacing(12)

        self.card_ok = self._card("今日成功", "0", "较昨日 +0")
        self.card_fail = self._card("今日失败", "0", "需要排查")
        self.card_time = self._card("平均耗时", "0ms", "近 10 次")

        cards_row.addWidget(self.card_ok)
        cards_row.addWidget(self.card_fail)
        cards_row.addWidget(self.card_time)

        layout.addLayout(cards_row)

        panel, panel_layout = self._panel("最近运行")

        self.table_recent = QtWidgets.QTableWidget(0, 4)
        self.table_recent.setHorizontalHeaderLabels(["时间", "任务", "状态", "耗时(ms)"])
        self.table_recent.horizontalHeader().setStretchLastSection(True)
        self.table_recent.verticalHeader().setVisible(False)
        self.table_recent.setShowGrid(False)
        self.table_recent.setAlternatingRowColors(False)
        self.table_recent.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_recent.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_recent.setSortingEnabled(True)

        panel_layout.addWidget(self.table_recent)

        layout.addWidget(panel, 1)
        return page

    def _build_tasks_page(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        grid = QtWidgets.QGridLayout(page)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)

        left_panel, left_layout = self._panel("创建任务")

        form = QtWidgets.QFormLayout()
        form.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        form.setFormAlignment(QtCore.Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self.input_name = QtWidgets.QLineEdit()
        self.input_name.setPlaceholderText("例如：BOSS 自动投递")

        self.input_type = QtWidgets.QComboBox()
        self.input_type.addItems(["登录并运行", "仅登录", "仅校验 Cookie"])

        self.input_priority = QtWidgets.QComboBox()
        self.input_priority.addItems(["低", "中", "高"])

        form.addRow("任务名称", self.input_name)
        form.addRow("类型", self.input_type)
        form.addRow("优先级", self.input_priority)

        left_layout.addLayout(form)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.setSpacing(10)

        btn_add = QtWidgets.QPushButton("添加")
        btn_add.setObjectName("Primary")
        btn_add.clicked.connect(self._add_task)

        btn_clear = QtWidgets.QPushButton("清空")
        btn_clear.setObjectName("Action")
        btn_clear.clicked.connect(self._clear_task_form)

        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_clear)
        btn_row.addStretch(1)

        left_layout.addLayout(btn_row)

        right_panel, right_layout = self._panel("任务列表")

        self.table_tasks = QtWidgets.QTableWidget(0, 3)
        self.table_tasks.setHorizontalHeaderLabels(["名称", "类型", "优先级"])
        self.table_tasks.horizontalHeader().setStretchLastSection(True)
        self.table_tasks.verticalHeader().setVisible(False)
        self.table_tasks.setShowGrid(False)
        self.table_tasks.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_tasks.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)

        right_layout.addWidget(self.table_tasks)

        grid.addWidget(left_panel, 0, 0)
        grid.addWidget(right_panel, 0, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 2)

        return page

    def _build_settings_page(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        panel, panel_layout = self._panel("设置（演示）")

        form = QtWidgets.QFormLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self.input_path = QtWidgets.QLineEdit()
        self.input_path.setPlaceholderText("例如：e:/personal-project/boos-auto")

        self.input_level = QtWidgets.QComboBox()
        self.input_level.addItems(["INFO", "DEBUG", "WARNING", "ERROR"])

        form.addRow("工作目录", self.input_path)
        form.addRow("日志级别", self.input_level)

        panel_layout.addLayout(form)

        btn_row = QtWidgets.QHBoxLayout()
        btn_row.setSpacing(10)

        btn_save = QtWidgets.QPushButton("保存")
        btn_save.setObjectName("Primary")
        btn_save.clicked.connect(self._save_settings)

        btn_reset = QtWidgets.QPushButton("重置")
        btn_reset.setObjectName("Danger")
        btn_reset.clicked.connect(self._reset_settings)

        btn_row.addWidget(btn_save)
        btn_row.addWidget(btn_reset)
        btn_row.addStretch(1)

        panel_layout.addLayout(btn_row)

        layout.addWidget(panel)
        layout.addStretch(1)
        return page

    def _seed_data(self) -> None:
        examples = [
            DemoRow(datetime.now().strftime("%H:%M:%S"), "登录并运行", "成功", 842),
            DemoRow(datetime.now().strftime("%H:%M:%S"), "仅校验 Cookie", "失败", 129),
            DemoRow(datetime.now().strftime("%H:%M:%S"), "登录并运行", "成功", 911),
        ]
        for row in examples:
            self._append_recent(row)

        # 统计卡片
        self._refresh_metrics()

        # 任务列表示例
        self._append_task("BOSS 自动投递", "登录并运行", "高")
        self._append_task("Cookie 校验", "仅校验 Cookie", "中")

    def _append_recent(self, row: DemoRow) -> None:
        sorting_enabled = self.table_recent.isSortingEnabled()
        if sorting_enabled:
            self.table_recent.setSortingEnabled(False)

        r = self.table_recent.rowCount()
        self.table_recent.insertRow(r)

        self.table_recent.setItem(r, 0, QtWidgets.QTableWidgetItem(row.created_at))
        self.table_recent.setItem(r, 1, QtWidgets.QTableWidgetItem(row.task))

        status_item = QtWidgets.QTableWidgetItem(row.status)
        if row.status == "成功":
            status_item.setForeground(QtGui.QBrush(_qcolor("#34d399")))
        elif row.status == "失败":
            status_item.setForeground(QtGui.QBrush(_qcolor("#fb7185")))
        else:
            status_item.setForeground(QtGui.QBrush(_qcolor("#eab308")))
        self.table_recent.setItem(r, 2, status_item)

        dur_item = QtWidgets.QTableWidgetItem(str(row.duration_ms))
        dur_item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.table_recent.setItem(r, 3, dur_item)

        self.table_recent.resizeColumnsToContents()

        if sorting_enabled:
            self.table_recent.setSortingEnabled(True)

    def _refresh_metrics(self) -> None:
        ok = 0
        fail = 0
        durations: list[int] = []

        for r in range(self.table_recent.rowCount()):
            status_item = self.table_recent.item(r, 2)
            dur_item = self.table_recent.item(r, 3)
            if status_item is None or dur_item is None:
                continue

            status = status_item.text()
            if status == "成功":
                ok += 1
            elif status == "失败":
                fail += 1

            try:
                durations.append(int(dur_item.text()))
            except ValueError:
                continue

        avg = int(sum(durations) / max(1, len(durations)))

        self.card_ok.findChild(QtWidgets.QLabel, "CardValue").setText(str(ok))
        self.card_fail.findChild(QtWidgets.QLabel, "CardValue").setText(str(fail))
        self.card_time.findChild(QtWidgets.QLabel, "CardValue").setText(f"{avg}ms")

    def _toast(self, text: str) -> None:
        t = Toast(text, self)
        t.adjustSize()
        geo = self.geometry()
        x = geo.x() + geo.width() - t.sizeHint().width() - 24
        y = geo.y() + 24
        t.move(x, y)
        t.show_for(1700)

    def _on_search(self) -> None:
        q = self.search.text().strip()
        if not q:
            self.status.showMessage("请输入搜索内容", 1800)
            return
        self._toast(f"搜索：{q}（演示）")

    def _simulate_run(self) -> None:
        # 纯演示：插入一条“运行中”记录，随后变为成功
        now = datetime.now().strftime("%H:%M:%S")
        pending = DemoRow(now, "登录并运行", "运行中", 0)
        self._append_recent(pending)
        self._refresh_metrics()
        self.status.showMessage("正在运行示例任务…", 1500)

        def finish() -> None:
            last = self.table_recent.rowCount() - 1
            if last < 0:
                return
            self.table_recent.item(last, 2).setText("成功")
            self.table_recent.item(last, 2).setForeground(QtGui.QBrush(_qcolor("#34d399")))
            self.table_recent.item(last, 3).setText("763")
            self._refresh_metrics()
            self._toast("任务完成：成功")
            self.status.showMessage("完成", 1200)

        QtCore.QTimer.singleShot(900, finish)

    def _append_task(self, name: str, kind: str, priority: str) -> None:
        r = self.table_tasks.rowCount()
        self.table_tasks.insertRow(r)
        self.table_tasks.setItem(r, 0, QtWidgets.QTableWidgetItem(name))
        self.table_tasks.setItem(r, 1, QtWidgets.QTableWidgetItem(kind))
        pri_item = QtWidgets.QTableWidgetItem(priority)
        if priority == "高":
            pri_item.setForeground(QtGui.QBrush(_qcolor("#fb7185")))
        elif priority == "中":
            pri_item.setForeground(QtGui.QBrush(_qcolor("#fbbf24")))
        else:
            pri_item.setForeground(QtGui.QBrush(_qcolor("#a7f3d0")))
        self.table_tasks.setItem(r, 2, pri_item)
        self.table_tasks.resizeColumnsToContents()

    def _add_task(self) -> None:
        name = self.input_name.text().strip()
        if not name:
            self.status.showMessage("任务名称不能为空", 1800)
            return
        kind = self.input_type.currentText()
        pri = self.input_priority.currentText()
        self._append_task(name, kind, pri)
        self._toast("已添加任务")
        self._clear_task_form()

    def _clear_task_form(self) -> None:
        self.input_name.clear()
        self.input_type.setCurrentIndex(0)
        self.input_priority.setCurrentIndex(1)

    def _save_settings(self) -> None:
        self._toast("设置已保存（演示）")
        self.status.showMessage("已保存", 1200)

    def _reset_settings(self) -> None:
        self.input_path.clear()
        self.input_level.setCurrentIndex(0)
        self._toast("已重置（演示）")
        self.status.showMessage("已重置", 1200)


def run_demo() -> int:
    app = QtWidgets.QApplication(sys.argv)

    app.setStyleSheet(app_stylesheet())

    w = DemoWindow()
    w.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run_demo())
