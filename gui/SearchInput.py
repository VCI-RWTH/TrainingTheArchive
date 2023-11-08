import os
from typing import Dict, Any

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QComboBox, QSizePolicy, QPushButton, QFileDialog, QLineEdit
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QSize
from PyQt6.QtGui import QKeyEvent, QIcon, QPaintEvent, QPainter, QPixmap, QMouseEvent, QImage, QDragEnterEvent, QDropEvent

BASE_PATH = os.path.dirname(__file__)


class SearchInput(QFrame):
    """
    This is the part of the search bar that is actually used to enter the search prompts.
    It also offers a search history to the user and allows them to, search for an image and apply filters.
    """

    text_search_clicked = pyqtSignal(str)
    image_search_clicked = pyqtSignal(str)
    filter_clicked = pyqtSignal()
    image_dropped = pyqtSignal(int)

    def __init__(self):
        super().__init__()

        self.initUI()
        self.initPolicies()

    def initUI(self) -> None:
        self.setProperty('qssClass', 'SearchInput')

        self.layout = QHBoxLayout()
        self.setLayout(self.layout)

        # Create the input field and connect the signals
        self.input_field = SearchBarComboBox()
        self.input_field.setCursor(Qt.CursorShape.IBeamCursor)
        self.input_field.return_pressed.connect(self.textSearch)
        self.input_field.activated.connect(self.textSearch)
        self.input_field.image_dropped.connect(self.image_dropped.emit)

        # Small function to make it easier to add a button to the layout
        def addButton(icon_path: str, slot: pyqtSlot, tooltip: str) -> QPushButton:
            button = QPushButton(QIcon(icon_path), '')
            button.setProperty('qssClass', 'SearchInputButton')
            button.setIconSize(QSize(20, 20))
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(slot)
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            button.setToolTip(tooltip)

            self.layout.addWidget(button)
            return button

        addButton(os.path.join(BASE_PATH, 'icons', 'SearchIcon.svg'), self.textSearch, 'Search')
        self.layout.addWidget(self.input_field)
        addButton(os.path.join(BASE_PATH, 'icons', 'ClockIcon.svg'), self.input_field.showPopup, 'Search History')
        addButton(os.path.join(BASE_PATH, 'icons', 'ImageSearchIcon.svg'), self.imageSearch, 'Search by Image')

        self.filter_button = addButton(os.path.join(BASE_PATH, 'icons', 'FilterIcon.svg'), self.filterClicked, 'Set Filters')

    def initPolicies(self) -> None:
        self.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

    def sizeHint(self) -> QSize:
        return QSize(500, 40)

    @pyqtSlot()
    def textSearch(self) -> None:
        """
        This function is called when the user presses enter or clicks the search button.
        It notifies the search bar that the user wants to search for the current text and stores the text to the history.
        """
        self.input_field.addCurrentItem()
        self.text_search_clicked.emit(self.input_field.currentText())

    @pyqtSlot()
    def imageSearch(self) -> None:
        """
        This function is called when the user clicks the image search button.
        It opens a file dialog and notifies the search bar that the user wants to search for the selected image.
        """
        image = QFileDialog.getOpenFileName(self, 'Select Image', '', 'image (*.jpg *.jpeg *.png *.tga *.bmp)')
        if image and image[0]:
            self.image_search_clicked.emit(image[0])

    @pyqtSlot()
    def filterClicked(self) -> None:
        """
        This function is called when the user clicks the filter button. It just passes it to the search bar.
        """
        self.filter_clicked.emit()

    def setFilterIcon(self, active: bool) -> None:
        """
        Sets the filter icon to active when the user has applied filters.
        :param active: Whether the filter icon should be active or not
        """
        if active:
            self.filter_button.setIcon(QIcon(os.path.join(BASE_PATH, 'icons', 'FilterIconActive.svg')))
        else:
            self.filter_button.setIcon(QIcon(os.path.join(BASE_PATH, 'icons', 'FilterIcon.svg')))

    def getLastSearchTerm(self) -> str:
        return self.input_field.itemText(0)

    def serialize(self) -> Dict[str, Any]:
        return {
            'last_searches': [self.input_field.itemText(i) for i in range(self.input_field.count())],
            'display_type': self.input_field.line_edit.display_type,
            'display_image_path': self.input_field.line_edit.display_image_path
        }

    def deserialize(self, data: Dict[str, Any]) -> None:
        self.input_field.clear()
        self.input_field.addItems(data['last_searches'])

        self.input_field.line_edit.setDisplayType(data['display_type'])

        if data['display_type'] == 'image':
            self.input_field.line_edit.setImage(data['display_image_path'])


class SearchBarComboBox(QComboBox):
    """
    The text field inside the search input to type a prompt into.
    It also offers a search history to re-search old prompts.
    """

    return_pressed = pyqtSignal()
    image_dropped = pyqtSignal(int)

    def __init__(self):
        super().__init__()

        self.initUI()
        self.initPolicies()

    def initUI(self) -> None:
        self.setProperty('qssClass', 'SearchInputField')

        # Configure the input field
        self.setEditable(True)
        self.setDuplicatesEnabled(True)
        self.setCursor(Qt.CursorShape.IBeamCursor)

        # Replace the line edit of the combo box with a custom one to be able to display images after an image search
        self.line_edit = SearchBarLineEdit()
        self.line_edit.image_dropped.connect(self.image_dropped.emit)
        self.setLineEdit(self.line_edit)
        self.lineEdit().setPlaceholderText('Search for e.g., a dog standing in front of a tree...')

    def initPolicies(self) -> None:
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setInsertPolicy(QComboBox.InsertPolicy.InsertAtTop)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """
        Override the key press event to search when the user presses enter.
        """
        if event.key() == Qt.Key.Key_Return:
            self.return_pressed.emit()
        else:
            super().keyPressEvent(event)

    def addCurrentItem(self) -> None:
        """
        Adds the current text to the search history.
        """
        if self.line_edit.display_type == 'text':
            self.insertItem(0, self.currentText())
        elif self.line_edit.display_type == 'image':
            self.insertItem(0, '<image search>')
        self.setCurrentIndex(0)


class SearchBarLineEdit(QLineEdit):
    """
    The line edit inside the search input to type a prompt into.
    It is extended to be able to display images.
    """

    image_dropped = pyqtSignal(int)

    def __init__(self):
        super().__init__()

        self.display_type = 'text'  # Stores the state of the line edit (display image or text)
        self.display_image_path = ''  # Stores the path of the image to display

        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """
        Override the drag enter event to be accept the format used by the app.
        """
        if event.mimeData().hasFormat('text/plain'):
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        """
        Override the drop event to be able to drop images into the line edit and check if it is an image from the app.
        """
        if event.mimeData().hasFormat('text/plain'):
            text = event.mimeData().text()
            type = text.split(':')[0]

            if type == 'image':
                image_id = int(text.split(':')[1])

                self.image_dropped.emit(image_id)

    def paintEvent(self, event: QPaintEvent) -> None:
        """
        Override the paint event to be able to display an image instead of text.
        """
        super().paintEvent(event)

        if self.display_type == 'image':
            painter = QPainter(self)

            pixmap = QPixmap(self.display_image_path)
            pixmap = pixmap.scaled(self.height(), self.width(), Qt.AspectRatioMode.KeepAspectRatio)

            painter.drawPixmap(0, 0, pixmap)

            painter.end()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """
        Override the mouse press event to remove image when to user wants to type a new prompt.
        """
        super().mousePressEvent(event)

        if self.display_type == 'image':
            self.setDisplayType('text')

    def setImage(self, image_path: str) -> None:
        """
        Sets the image that is displayed in the line edit, if the display type is set to image.

        :param image_path: The path of the image to display
        """
        self.display_image_path = image_path

    def setDisplayType(self, display_type: str) -> None:
        """
        Sets the display type of the line edit. Either 'text' or 'image'.

        :param display_type: The display type to set
        """
        if self.display_type != display_type:
            self.display_type = display_type

            if display_type == 'image':
                self.setReadOnly(True)
                self.setText(' ')  # Prevent the placeholder from being displayed
            elif display_type == 'text':
                self.setReadOnly(False)
                self.setText('')

            self.update()
