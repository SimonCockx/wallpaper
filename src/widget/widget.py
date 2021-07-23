from typing import Any

from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import QSize
from PySide6.QtGui import QColor, Qt, QIcon, QScreen
from PySide6.QtWidgets import QApplication, QMessageBox, QDialog

from handler.configmanager import ConfigField
from handler.manager import WallpaperManager, WallpaperObserver
from timer.timer import WallpaperTimer


class WallpaperWidget(WallpaperObserver, QtWidgets.QWidget):
    icon_color = QColor(150, 210, 255, 255)
    default_button_size = 30

    def __init__(self, manager: WallpaperManager, timer: WallpaperTimer,
                 previous_icon: str,
                 pause_icon: str,
                 play_icon: str,
                 next_icon: str,
                 turn_left_icon: str,
                 turn_right_icon: str,
                 delete_icon: str,
                 explorer_icon: str,
                 config_icon: str,
                 tools_icon: str,
                 initially_expanded: bool = False):
        super().__init__(f=QtCore.Qt.WindowStaysOnBottomHint
                         | QtCore.Qt.CustomizeWindowHint
                         | QtCore.Qt.FramelessWindowHint
                         | QtCore.Qt.MSWindowsFixedSizeDialogHint
                         | QtCore.Qt.Tool
                         )

        self.manager = manager
        self.timer = timer

        self.pause_icon = self._create_icon(pause_icon)
        self.play_icon = self._create_icon(play_icon)

        self.previous = self._create_button(self._create_icon(previous_icon))
        self.play_or_pause = self._create_button(
            self.pause_icon if self.timer.is_running else self.play_icon)
        self.next = self._create_button(self._create_icon(next_icon))
        self.turn_left = self._create_button(self._create_icon(turn_left_icon))
        self.turn_right = self._create_button(self._create_icon(turn_right_icon))
        self.delete = self._create_button(self._create_icon(delete_icon))
        self.open_explorer = self._create_button(self._create_icon(explorer_icon))
        self.open_config = self._create_button(self._create_icon(config_icon))
        self.tools = self._create_button(self._create_icon(tools_icon))
        self.tools.setCheckable(True)
        self.tools.setChecked(not initially_expanded)

        self.action_buttons = [self.previous, self.play_or_pause, self.next, self.turn_left, self.turn_right,
                               self.delete, self.open_explorer, self.open_config]

        self.hlayout = QtWidgets.QHBoxLayout(self)
        self.layout().setContentsMargins(5, 5, 5, 5)
        self.hlayout.setSpacing(0)
        for btn in self.action_buttons:
            self.hlayout.addWidget(btn)
        self.hlayout.addWidget(self.tools)

        self.previous.clicked.connect(self._handle_previous)
        self.play_or_pause.clicked.connect(self._handle_play_or_pause)
        self.next.clicked.connect(self._handle_next)
        self.turn_left.clicked.connect(self._handle_turn_left)
        self.turn_right.clicked.connect(self._handle_turn_right)
        self.delete.clicked.connect(self._handle_delete)
        self.open_explorer.clicked.connect(self._handle_open_explorer)
        self.open_config.clicked.connect(self._handle_open_config)
        self.tools.clicked.connect(self._handle_tool_toggle)

        self._update_button_size()

        if initially_expanded:
            self.expand()
        else:
            self.collapse()

    def start(self):
        self.manager.subscribe(self)
        self.show()

    def _create_icon(self, path: str) -> QIcon:
        pixmap = QIcon(path).pixmap(QSize(512, 512))
        mask = pixmap.createMaskFromColor(QColor('black'), Qt.MaskOutColor)
        pixmap.fill(self.icon_color)
        pixmap.setMask(mask)
        return QIcon(pixmap)

    def _create_button(self, icon: QIcon):
        btn = QtWidgets.QPushButton(icon, '')
        return btn

    def expand(self):
        for btn in self.action_buttons:
            btn.show()
        self._refresh_geometry()
        self.setWindowOpacity(0.95)

    def collapse(self):
        for btn in self.action_buttons:
            btn.hide()
        self._refresh_geometry()
        self.setWindowOpacity(0.6)

    def _refresh_geometry(self):
        self.setFixedSize(self.hlayout.sizeHint())
        self._move_to_top_right()

    def _move_to_top_right(self):
        tr = QScreen.availableGeometry(QApplication.primaryScreen()).topRight()
        geo = self.frameGeometry()
        geo.moveTopRight(tr - QtCore.QPoint(10, -10))
        self.move(geo.topLeft())

    def on_config_change(self, field: ConfigField, value: Any) -> None:
        if field == ConfigField.WIDGET_SCALE:
            self._update_button_size()
            self._refresh_geometry()

    def _update_button_size(self):
        s = self.default_button_size * self.manager.get_config(ConfigField.WIDGET_SCALE)
        for btn in self.action_buttons:
            btn.setIconSize(QSize(s, s))
        self.tools.setIconSize(QSize(s, s))

    @QtCore.Slot()
    def _handle_previous(self):
        self.manager.previous()

    @QtCore.Slot()
    def _handle_play_or_pause(self):
        if self.timer.is_running:
            self.timer.pause()
            self.play_or_pause.setIcon(self.play_icon)
        else:
            self.timer.resume()
            self.play_or_pause.setIcon(self.pause_icon)

    @QtCore.Slot()
    def _handle_next(self):
        self.manager.next()

    @QtCore.Slot()
    def _handle_turn_left(self):
        self.manager.rotate_current_left()

    @QtCore.Slot()
    def _handle_turn_right(self):
        self.manager.rotate_current_right()

    @QtCore.Slot()
    def _handle_delete(self):
        msg_box = QMessageBox()
        msg_box.setWindowTitle("Delete wallpaper")
        msg_box.setText(
            f"Are you sure you want to delete {self.manager.current_source.get_label(self.manager.current_path)}?")
        msg_box.setInformativeText("This action cannot be undone.")
        msg_box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        msg_box.setDefaultButton(QMessageBox.Ok)
        is_running = self.timer.is_running
        if is_running:
            self.timer.pause()
        if msg_box.exec() == QMessageBox.Ok:
            self.manager.delete_current()
        if is_running:
            self.timer.resume()

    @QtCore.Slot()
    def _handle_open_explorer(self):
        self.manager.show_source_of_current()

    @QtCore.Slot()
    def _handle_open_config(self):
        self.manager.open_config()

    @QtCore.Slot()
    def _handle_tool_toggle(self):
        if self.tools.isChecked():
            self.collapse()
        else:
            self.expand()
