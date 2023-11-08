from PyQt6.QtWidgets import QSplitter, QSplitterHandle, QSizePolicy
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QPaintEvent, QPainter, QPen, QColor

from gui.Colors import SECONDARY_COLOR


class Splitter(QSplitter):
    """
    Subclass of QSplitter that uses a custom handle.
    """
    def createHandle(self) -> QSplitterHandle:
        return SplitterHandle(self.orientation(), self)


class SplitterHandle(QSplitterHandle):
    """
    Subclass of QSplitterHandle that has dots in the middle of the handle
    """

    # Options for the dots (settings are for the vertical orientation and will be rotated by 90 degrees for horizontal)
    dot_spacing_horizontal = 4
    dot_spacing_vertical = 1
    dot_size = 4
    dot_rows = 1
    dot_columns = 3
    padding = 2

    def __init__(self, orientation: Qt.Orientation, parent: QSplitter):
        super().__init__(orientation, parent)

        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        self.setContentsMargins(1, 1, 1, 1)

    def sizeHint(self) -> QSize:
        """
        Adjust the size hint based on how many dots there are
        """
        width = self.dot_size * self.dot_columns + self.dot_spacing_horizontal * (self.dot_columns - 1) + self.padding * 2
        height = self.dot_size * self.dot_rows + self.dot_spacing_vertical * (self.dot_rows - 1) + self.padding * 2

        if self.orientation() == Qt.Orientation.Vertical:
            return QSize(width, height)
        else:
            return QSize(height, width)

    def paintEvent(self, event: QPaintEvent) -> None:
        """
        Override the paint event to draw the dots
        """
        super().paintEvent(event)

        painter = QPainter(self)

        # Configure painter
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(SECONDARY_COLOR))

        width = self.width()
        height = self.height()

        # Determine the width and rect of the bounding rect of the dots
        dots_rect_width = self.dot_size * self.dot_columns + self.dot_spacing_horizontal * (self.dot_columns - 1)
        dots_rect_height = self.dot_size * self.dot_rows + self.dot_spacing_vertical * (self.dot_rows - 1)

        # Draw dots
        for row in range(self.dot_rows):
            for column in range(self.dot_columns):
                if self.orientation() == Qt.Orientation.Vertical:
                    # "width / 2" to start in the middle of the handle
                    # "- dots_rect_width / 2" to draw the first dot at the border of the dots bounding rect
                    # "+ column * (self.dot_size + self.dot_spacing_horizontal)" to offset each dot by the dot size and spacing
                    x = int(width / 2 - dots_rect_width / 2 + column * (self.dot_size + self.dot_spacing_horizontal))
                    y = int(height / 2 - dots_rect_height / 2 + row * (self.dot_size + self.dot_spacing_vertical))

                    painter.drawEllipse(x, y, self.dot_size, self.dot_size)
                else:
                    x = int(width / 2 - dots_rect_height / 2 + row * (self.dot_size + self.dot_spacing_vertical))
                    y = int(height / 2 - dots_rect_width / 2 + column * (self.dot_size + self.dot_spacing_horizontal))

                    painter.drawEllipse(x, y, self.dot_size, self.dot_size)
