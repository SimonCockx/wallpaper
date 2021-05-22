import logging
import os
import sys

from PySide6 import QtWidgets
from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette, QColor

projectdir = os.path.dirname(os.path.dirname(__file__))
tempdir = os.path.join(projectdir, 'temp')
config_path = os.path.join(projectdir, 'config.ini')
fontsdir = os.path.join(projectdir, 'assets', 'fonts')
iconsdir = os.path.join(projectdir, 'assets', 'icons')
logging.basicConfig(filename=os.path.join(projectdir, 'wallpapers.log'), format='%(asctime)s %(levelname)s %(message)s',
                    filemode='w', level=logging.INFO)


from src.handler.manager import WallpaperManager  # noqa: E402
from src.timer.timer import WallpaperTimer  # noqa: E402
from src.widget.widget import WallpaperWidget  # noqa: E402


manager = WallpaperManager(
    os.path.join(projectdir, 'config.ini'),
    tempdir,
    os.path.join(fontsdir, 'Arial.ttf'),
)
timer = WallpaperTimer(manager)

manager.start()
timer.start()

app = QtWidgets.QApplication([])
# Force the style to be the same on all OSs:
app.setStyle("Fusion")

# Now use a palette to switch to dark colors:
palette = QPalette()
palette.setColor(QPalette.Window, QColor(53, 53, 53))
palette.setColor(QPalette.WindowText, Qt.white)
palette.setColor(QPalette.Base, QColor(25, 25, 25))
palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
palette.setColor(QPalette.ToolTipBase, Qt.black)
palette.setColor(QPalette.ToolTipText, Qt.white)
palette.setColor(QPalette.Text, Qt.white)
palette.setColor(QPalette.Button, QColor(53, 53, 53))
palette.setColor(QPalette.ButtonText, Qt.white)
palette.setColor(QPalette.BrightText, Qt.red)
palette.setColor(QPalette.Link, QColor(42, 130, 218))
palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
palette.setColor(QPalette.HighlightedText, Qt.black)
app.setPalette(palette)
widget = WallpaperWidget(manager, timer,
                         os.path.join(iconsdir, 'previous.svg'),
                         os.path.join(iconsdir, 'pause.svg'),
                         os.path.join(iconsdir, 'play.svg'),
                         os.path.join(iconsdir, 'next.svg'),
                         os.path.join(iconsdir, 'turn_left.svg'),
                         os.path.join(iconsdir, 'turn_right.svg'),
                         os.path.join(iconsdir, 'explorer.svg'),
                         os.path.join(iconsdir, 'config.svg'),
                         os.path.join(iconsdir, 'tools.svg'),
                         initially_expanded=False
                         )
widget.start()
sys.exit(app.exec())
