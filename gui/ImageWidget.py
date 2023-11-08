from typing import Callable

from PyQt6.QtWidgets import QLabel, QApplication, QSizePolicy, QMenu, QHBoxLayout
from PyQt6.QtCore import Qt, QMimeData, pyqtSignal, pyqtSlot, QSize, pyqtProperty, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QDrag, QResizeEvent, QMouseEvent, QPixmap, QContextMenuEvent, QIcon, QKeyEvent

from gui.PreviewWindow import PreviewWindow


class ImageWidget(QLabel):
    """
    A widget to display an image in a layout.
    It can be added to the canvass by drag & drop or double click
    """

    double_clicked = pyqtSignal(int)
    add_triggered = pyqtSignal(int)
    put_away_triggered = pyqtSignal(int)

    def __init__(self, id: int, path: str, artsearch):
        super().__init__()

        self.artsearch = artsearch

        self.id = id
        self.pixmap_original = QPixmap(path)  # The original pixmap is stored to be able to scale it later

        # Create the preview window for the image
        self.preview_window = PreviewWindow(self.artsearch)
        self.preview_window.setImage(id, path)

        self.initUI()
        self.initContextMenu()

    def initUI(self) -> None:
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setPixmap(self.pixmap_original)

    def initContextMenu(self) -> None:
        self.context_menu = QMenu()

        preview_action = self.context_menu.addAction(QIcon(''), 'Show Preview')
        preview_action.triggered.connect(self.preview_window.show)

        add_action = self.context_menu.addAction(QIcon(''), 'Add to Canvas')
        add_action.triggered.connect(lambda: self.add_triggered.emit(self.id))

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        self.context_menu.exec(event.globalPos())

        super().contextMenuEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """
        Emit the double_clicked signal when the widget is double-clicked to add it to the canvas
        """
        self.double_clicked.emit(self.id)

        super().mouseDoubleClickEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """
        Start a drag & drop operation when the widget is dragged
        Store the image id in the mime data as a string and set the pixmap as the drag pixmap.

        The mime data for this application is a simple string with the format 'type:content'
        """
        mime_data = QMimeData()
        mime_data.setText('image:' + str(self.id))

        drag = QDrag(self)
        drag.setMimeData(mime_data)

        pixmap_scaled = self.pixmap_original.scaled(60, 60, Qt.AspectRatioMode.KeepAspectRatio)
        drag.setPixmap(pixmap_scaled)
        drag.setHotSpot(pixmap_scaled.rect().center())

        QApplication.setOverrideCursor(Qt.CursorShape.ClosedHandCursor)
        drag.exec(Qt.DropAction.MoveAction)
        QApplication.restoreOverrideCursor()

        # The image is removed from its parent layout when it is added to the canvas

        super().mouseMoveEvent(event)

class ImageWidgetSearchBar(ImageWidget):
    """
    Extend the default ImageWidget to add logic that is needed when displaying an image in the search bar (results display)
    It is able to use a flip animation to show or hide itself.
    """

    preview_left_arrow_clicked = pyqtSignal(int)
    preview_right_arrow_clicked = pyqtSignal(int)

    def __init__(self, id: int, path: str, artsearch):
        super().__init__(id, path, artsearch)

        self._pixmap_width = 0
        # This variable is used to store whether the widget is currently animating or not
        # This is needed to prevent the widget from being resized while it is animating
        self.animating = False

        self.preview_window.left_arrow_clicked.connect(self.preview_left_arrow_clicked.emit)
        self.preview_window.right_arrow_clicked.connect(self.preview_right_arrow_clicked.emit)

        self.initContextMenu()

    def initContextMenu(self) -> None:
        """
        Override the default context menu to add the 'Put Away' action to add the image directly to the box
        """
        super().initContextMenu()

        put_away_action = self.context_menu.addAction(QIcon(''), 'Put Away')
        put_away_action.triggered.connect(lambda: self.put_away_triggered.emit(self.id))

    def resizeEvent(self, event: QResizeEvent) -> None:
        """
        Override the default resize event to keep rescale the image when the results display is resized
        """
        if not self.animating:
            self.setPixmap(self.pixmap_original.scaled(9999, self.height(), Qt.AspectRatioMode.KeepAspectRatio))
            self.setFixedWidth(self.pixmap().width())

        super().resizeEvent(event)

    @pyqtSlot()
    def toggleAnimating(self) -> None:
        self.animating = not self.animating

    def flipIn(self, callback: Callable=None) -> None:
        """
        Show the widget with a flip animation

        :param callback: A function to be called when the animation is finished
        """
        self.toggleAnimating()
        self.show()
        self.anim = QPropertyAnimation(self, b'pixmap_width')
        self.anim.setDuration(250)
        self.anim.setStartValue(0)
        self.anim.setEndValue(self.pixmap().width())
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.finished.connect(self.toggleAnimating)
        if callback:
            self.anim.finished.connect(callback)
        self.anim.start()

    def flipOut(self, callback: Callable=None) -> None:
        """
        Hide the widget with a flip animation

        :param callback: A function to be called when the animation is finished
        """
        self.toggleAnimating()
        self.anim = QPropertyAnimation(self, b'pixmap_width')
        self.anim.setDuration(250)
        self.anim.setStartValue(self.pixmap().width())
        self.anim.setEndValue(0)
        self.anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self.anim.finished.connect(self.hide)
        self.anim.finished.connect(self.toggleAnimating)
        if callback:
            self.anim.finished.connect(callback)
        self.anim.start()

    @pyqtProperty(int)
    def pixmap_width(self) -> int:
        return self._pixmap_width

    @pixmap_width.setter
    def pixmap_width(self, width) -> None:
        self._pixmap_width = width

        self.setPixmap(self.pixmap_original.scaled(width, self.height(), Qt.AspectRatioMode.IgnoreAspectRatio))


class ImageWidgetBox(ImageWidget):
    """
    Extend the default ImageWidget to add logic that is needed when displaying an image in the box
    """
    def __init__(self, id: int, path: str, artsearch):
        super().__init__(id, path, artsearch)

        self.margin = 20

    def setImageWidth(self, width: int) -> None:
        self.setPixmap(self.pixmap_original.scaled(width - self.margin, 9999, Qt.AspectRatioMode.KeepAspectRatio))
        self.setFixedHeight(self.pixmap().height())
