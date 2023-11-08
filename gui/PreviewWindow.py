from PyQt6.QtWidgets import QWidget, QHBoxLayout, QFormLayout, QLabel, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QKeyEvent

from SearchEngine import METASearch


class PreviewWindow(QWidget):
    """
    This class represents the preview window that is used to preview an image.
    In the preview window there is a larger version of the image and the metadata of the image.
    There is a difference between the preview window in the search bar and on the canvas.
    In the SearchBar there can be more than one PreviewWindow and the user can click through the search results
    using the arrow keys
    On the canvas there is only one PreviewWindow and the user can click on the image to update the preview window
    When opening/showing this widget that opens the preview window has to set the id and the path of the image
    """

    left_arrow_clicked = pyqtSignal(int)
    right_arrow_clicked = pyqtSignal(int)

    def __init__(self, artsearch):
        super().__init__()

        self.artsearch = artsearch

        # The initial id is set to -1 (custom image). The id and path have to be set before showing the widget
        self.image_id = -1
        self.pixmap = None

        self.initUI()

    def initUI(self) -> None:
        self.setWindowTitle('Object preview')

        # Set flag so the window is always on top
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)

        self.layout = QHBoxLayout()
        self.setLayout(self.layout)

        # Creat the label where to image will be displayed
        self.image_label = QLabel()
        self.layout.addWidget(self.image_label)

        self.meta_data_layout = QFormLayout()
        self.meta_data_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.DontWrapRows)
        self.meta_data_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self.layout.addLayout(self.meta_data_layout)


    def setImage(self, image_id: int, path: str) -> None:
        """
        Sets the image that is displayed in the preview window

        :param image_id: The id of the image (-1 for custom images that are not in the embedding)
        :param path: The path to the image
        """
        self.image_id = image_id

        # Load the image and scale it to 400x400
        self.pixmap = QPixmap(path).scaled(400, 400, Qt.AspectRatioMode.KeepAspectRatio)
        self.image_label.setPixmap(self.pixmap)

        self.meta_data_layout = QFormLayout()
        self.meta_data_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.DontWrapRows)
        self.meta_data_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self.layout.addLayout(self.meta_data_layout)

        # Check if the image is a custom image or in the embedding
        if self.image_id != -1:
            # Add the metadata for the image by using the columns of the metadata dataframe (search engine keys)
            # as the labels and the data from the search engine as the data
            for key, search in self.artsearch.search_engines.items():
                if isinstance(search, METASearch):
                    label = QLabel(f'{key}:')

                    data = search.search_by_id(self.image_id)

                    # Check if the data is nan and replace it with an empty string in that case
                    if data == 'nan':
                        data = ''

                    data_label = QLabel(data)
                    data_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
                    data_label.setWordWrap(True)

                    self.meta_data_layout.addRow(label, data_label)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """
        Navigate through the search results using the arrow keys and hide the preview window when the space key is pressed
        """
        if event.key() == Qt.Key.Key_Space:
            self.hide()
        if event.key() == Qt.Key.Key_Left:
            self.left_arrow_clicked.emit(self.image_id)
        if event.key() == Qt.Key.Key_Right:
            self.right_arrow_clicked.emit(self.image_id)

        super().keyPressEvent(event)
