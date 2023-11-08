from typing import List, Dict, Any

from PyQt6.QtWidgets import QScrollArea, QPushButton, QSizePolicy, QWidget, QVBoxLayout, QHBoxLayout, QScrollBar
from PyQt6.QtCore import Qt, QSize, QPointF, pyqtSignal, pyqtProperty, QPropertyAnimation, QParallelAnimationGroup, QSequentialAnimationGroup, QEasingCurve
from PyQt6.QtGui import QPaintEvent, QPainter, QPainterPath, QPolygonF, QPen, QBrush, QResizeEvent, QColor

from gui.ImageWidget import ImageWidgetBox
from gui.Note import NoteWidget
from gui.Colors import WHITE, ICON_COLOR


class Box(QScrollArea):
    """
    The box that contains all the images and notes that were removed from the canvas.
    All images that are inside the box should be a negative instance for the search.
    To ensure this, adding images should be done by the CanvasScene instance.

    The box can be opened and closed by clicking the button in the top right corner of the Canvas.
    It will then slide out from the right side of the canvas.

    The user is able to add the images back to the canvas, resulting in a positive instance for the search.
    """

    image_double_clicked = pyqtSignal(int)
    add_context_menu_triggered = pyqtSignal(int)

    def __init__(self):
        super().__init__()

        # artsearch is set by the main window after the canvas is created
        self.artsearch = None

        # Stores the image widgets that are inside the box ({"image_id": ImageWidgetBox}})
        self.images = {}

        self.initUI()
        self.initPolicies()

    def initUI(self) -> None:
        """
        Set up the layout of the widget
        It consists of two columns, in which the images and notes are placed.
        Widgets are added in a way that tries to balance the height of the columns.
        """
        self.setWidgetResizable(True)

        self.main_widget = QWidget()

        self.setVerticalScrollBar(QScrollBar(self))
        self.verticalScrollBar().setProperty('qssClass', 'BoxScrollBar')

        self.layout = QVBoxLayout()
        self.column_layout = QHBoxLayout()
        self.first_column = QVBoxLayout()
        self.second_column = QVBoxLayout()

        self.column_layout.addLayout(self.first_column)
        self.column_layout.addLayout(self.second_column)
        self.main_widget.setLayout(self.layout)

        # Add this spacer at the bottom of the widget, to align all images correctly
        self.spacer = QWidget()
        self.spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.spacer.setMinimumSize(0, 0)

        self.layout.addLayout(self.column_layout)
        self.layout.addWidget(self.spacer)

        self.setWidget(self.main_widget)

    def initPolicies(self) -> None:
        self.setFocusPolicy(Qt.FocusPolicy.WheelFocus)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def minimumSizeHint(self):
        """
        Override the minimumSizeHint to allow the box to smoothly shrink to 0 and not stay stuck at the minimum size hint
        """
        return QSize(0, 0)

    def resizeEvent(self, event: QResizeEvent) -> None:
        """
        Override the resize event to update the width of the images when the widget is resized
        This is used to make sure the images are always half the width of the widget

        In this function the width of the widget is also stored when it is shown, to always open the box to the same size it was closed
        """
        # Update the width of the images
        for image in self.images.values():
            image.setImageWidth(self.width() // 2)

        super().resizeEvent(event)

    def createImage(self, image_id: int) -> ImageWidgetBox:
        """
        Create an ImageWidgetBox instance for the given image_id.
        It connects the double_clicked and add_triggered signals to the corresponding signals.

        :param image_id: An image id
        :return: The created ImageWidgetBox instance
        """
        image = ImageWidgetBox(image_id, self.artsearch.getImagePath(image_id), self.artsearch)
        image.double_clicked.connect(self.image_double_clicked.emit)
        image.add_triggered.connect(self.add_context_menu_triggered.emit)
        image.setImageWidth(self.width() // 2)

        return image

    def addImage(self, image_id: int) -> None:
        """
        Add an image to the box.
        The image is placed in the column with the least height.

        :param image_id: The id of the image to add
        """
        # Create the image widget
        image = self.createImage(image_id)

        self.images[str(image_id)] = image

        self.artsearch.setImageNegative(image_id)

        # Add the image to the first column and rebalance the columns
        self.first_column.addWidget(image, alignment=Qt.AlignmentFlag.AlignTop)
        self.updateLayout()

    def removeImage(self, image_id: int) -> None:
        """
        Remove an image from the box.

        :param image_id: The id of the image to remove
        """
        # Remove the image from the layout and the images dict if it exists
        if str(image_id) in self.images:
            self.images[str(image_id)].setParent(None)
            self.images.pop(str(image_id))

        # Rebalance the columns
        self.updateLayout()

    def addWidget(self, widget: QWidget) -> None:
        """
        Add a widget to the box.
        The widget is placed in the column with the least height.

        This function is used to add notes to the box.

        :param widget: The widget to add
        """
        # Add the widget to the first column and rebalance the columns
        self.first_column.addWidget(widget, alignment=Qt.AlignmentFlag.AlignTop)
        self.updateLayout()

    def removeWidget(self, widget: QWidget) -> None:
        """
        Remove a widget from the box.

        :param widget: The widget to remove
        """
        widget.setParent(None)
        self.updateLayout()

    def removeNoteByContent(self, content: str) -> None:
        """
        Remove a note from the box by its content.
        This can remove the wrong note if there are multiple notes with the same content. Use with caution.

        :param content: The content of the note to remove
        """
        for i in range(self.first_column.count()):
            widget = self.first_column.itemAt(i).widget()
            if isinstance(widget, NoteWidget) and widget.content == content:
                self.removeWidget(widget)
                self.updateLayout()
                return
        for i in range(self.second_column.count()):
            widget = self.second_column.itemAt(i).widget()
            if isinstance(widget, NoteWidget) and widget.content == content:
                self.removeWidget(widget)
                self.updateLayout()
                return

    def updateLayout(self) -> None:
        """
        Rebalance the columns. So that the columns are as close to the same height as possible.
        """
        first_column_height = 0
        second_column_height = 0

        # Calculate the height of the columns
        for i in range(self.first_column.count()):
            widget = self.first_column.itemAt(i).widget()
            first_column_height += widget.height()
        for i in range(self.second_column.count()):
            widget = self.second_column.itemAt(i).widget()
            second_column_height += widget.height()

        # Calculate the difference between the columns
        diff = first_column_height - second_column_height

        # Move the last widget from the highest column to the lowest column if the difference is bigger than the height of the last widget
        if diff > 0:
            # First column is higher than second column
            last_widget = self.first_column.itemAt(self.first_column.count() - 1).widget()
            if diff - last_widget.height() > 0:
                last_widget.setParent(None)
                self.second_column.addWidget(last_widget, alignment=Qt.AlignmentFlag.AlignTop)
        elif diff < 0:
            # Second column is higher than first column
            last_widget = self.second_column.itemAt(self.second_column.count() - 1).widget()
            if diff + last_widget.height() < 0:
                last_widget.setParent(None)
                self.first_column.addWidget(last_widget, alignment=Qt.AlignmentFlag.AlignTop)

    def clear(self) -> None:
        """
        Removes all widgets from the box
        """
        for i in reversed(range(self.first_column.count())):
            self.first_column.itemAt(i).widget().setParent(None)

        for i in reversed(range(self.second_column.count())):
            self.second_column.itemAt(i).widget().setParent(None)

    def serialize(self) -> Dict[str, Any]:
        return {
            'first_column': self.serializeColumn(self.first_column),
            'second_column': self.serializeColumn(self.second_column)
        }

    def serializeColumn(self, column: QVBoxLayout) -> List[Any]:
        content = []

        for i in range(column.count()):
            widget = column.itemAt(i).widget()
            if isinstance(widget, ImageWidgetBox):
                content.append(widget.id)
            elif isinstance(widget, NoteWidget):
                content.append({
                    'type': 'note',
                    'text': widget.content,
                    'color': widget.color.name()
                })

        return content

    def deserialize(self, data: Dict[str, Any]) -> None:
        self.images = {}
        self.clear()

        self.deserializeColumn(self.first_column, data['first_column'])
        self.deserializeColumn(self.second_column, data['second_column'])

    def deserializeColumn(self, column: QVBoxLayout, data: Dict[str, Any]):
        for item in data:
            if isinstance(item, int):
                image = self.createImage(item)
                column.addWidget(image)
            elif isinstance(item, dict):
                if item['type'] == 'note':
                    widget = NoteWidget(item['text'], QColor(item['color']))
                    column.addWidget(widget)


class BoxButton(QPushButton):
    """
    A button that is used to open the box.
    It has a custom animation and always represents the current state of the box:
    If the box is open the box icon is an open box and vice versa.
    """

    pen = QPen(QColor(ICON_COLOR), 1, cap=Qt.PenCapStyle.RoundCap, join=Qt.PenJoinStyle.RoundJoin)
    brush = QBrush(QColor(WHITE))

    def __init__(self):
        super().__init__()

        # The offset of the entire box icon
        # The box is offset to allow it to shake, when an item is added to it
        self._box_offset = QPointF(5, 5)

        # The offset of the top of the box
        # The top is offset to animate the opening and closing of the box
        self._top_offset = QPointF(0, 0)
        self._top_opacity = 1.0

        # The width and height of the box icon
        self.box_width = 30
        self.box_height = 30

        # Store whether the box (button) is currently open or not
        self.open = False

        self.setToolTip('Removed Images')

        self.initPolicies()
        self.initAnimations()

    def initPolicies(self) -> None:
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def sizeHint(self) -> QSize:
        return QSize(self.box_width + int(self.box_offset.x()) * 2,
                     self.box_height + int(self.box_offset.y()) * 2)

    def initAnimations(self) -> None:
        """
        Initializes the animations for opening and closing the box.
        """
        open_close_duration = 300

        # Adds an animation to a given animation group
        # Used to reduce code duplication when creating the animations
        def addAnimation(attribute, start_value, end_value, duration, easing_curve, group) -> None:
            animation = QPropertyAnimation(self, attribute)
            animation.setDuration(duration)
            animation.setEasingCurve(easing_curve)
            animation.setStartValue(start_value)
            animation.setEndValue(end_value)
            group.addAnimation(animation)

        self.close_animation = QParallelAnimationGroup()
        addAnimation(b'top_opacity', 0.0, 1.0, open_close_duration, QEasingCurve.Type.OutCubic, self.close_animation)
        addAnimation(b'top_offset', QPointF(0, -self.box_offset.y()), self.top_offset, open_close_duration, QEasingCurve.Type.OutCubic, self.close_animation)

        self.open_animation = QParallelAnimationGroup()
        addAnimation(b'top_opacity', 1.0, 0.0, open_close_duration, QEasingCurve.Type.OutCubic, self.open_animation)
        addAnimation(b'top_offset', self.top_offset, -self.box_offset.y(), open_close_duration, QEasingCurve.Type.OutCubic, self.open_animation)

        self.shake_animation = QSequentialAnimationGroup()
        keyframes = [QPointF(self.box_offset.x() * -0.7 , self.box_offset.y() * -0.2),
                     QPointF(self.box_offset.x() * 0.5, self.box_offset.y() * 0.8),
                     QPointF(self.box_offset.x() * 0.2, self.box_offset.y() * 0.1),
                     QPointF(0, 0)]
        for i in range(len(keyframes) - 1):
            addAnimation(b'box_offset', self.box_offset + keyframes[i], self.box_offset + keyframes[i + 1], 70, QEasingCurve.Type.OutCubic, self.shake_animation)

    def paintEvent(self, event: QPaintEvent) -> None:
        """
        Draws the box icon depending on the current state of the box.
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.setPen(self.pen)
        painter.setBrush(self.brush)
        painter.drawPath(self.createBottomOutsidePath())

        painter.setBrush(QBrush(QColor('#35322f')))
        painter.drawPath(self.createBottomInsidePath())

        painter.setBrush(self.brush)
        painter.setOpacity(self.top_opacity)
        painter.drawPath(self.createTopPath())

    def createTopPath(self) -> QPainterPath:
        """
        Creates the path for the top of the box.
        This is its own method to not clutter the paintEvent method.
        """
        path = QPainterPath()

        height = self.box_height / 7
        x_offset = self.top_offset.x() + self.box_offset.x()
        y_offset = self.top_offset.y() + self.box_offset.y()

        left_point = QPointF(x_offset + 0,
                             y_offset + self.box_height / 5)
        right_point = QPointF(x_offset + self.box_width,
                              y_offset + self.box_height / 5)
        top_middle_point = QPointF(x_offset + self.box_width / 2,
                                   y_offset + 0)
        bottom_middle_point = QPointF(x_offset + self.box_width / 2,
                                      y_offset + (self.box_height / 5) * 2)

        top_polygon = QPolygonF()
        top_polygon << top_middle_point \
                    << right_point \
                    << bottom_middle_point \
                    << left_point \
                    << top_middle_point
        path.addPolygon(top_polygon)

        left_polygon = QPolygonF()
        left_polygon << left_point \
                     << left_point + QPointF(0, height) \
                     << bottom_middle_point + QPointF(0, height) \
                     << bottom_middle_point \
                     << left_point
        path.addPolygon(left_polygon)

        right_polygon = QPolygonF()
        right_polygon << right_point \
                      << right_point + QPointF(0, height) \
                      << bottom_middle_point + QPointF(0, height) \
                      << bottom_middle_point \
                      << right_point
        path.addPolygon(right_polygon)

        return path

    def createBottomOutsidePath(self) -> QPainterPath:
        """
        Creates the path for the bottom part of the box that is seen from outside.
        This is its own method to not clutter the paintEvent method.
        """
        path = QPainterPath()

        height = self.box_height / 1.8
        x_offset = self.box_offset.x()
        y_offset = self.box_offset.y()
        x_distance_from_top = 2

        left_point = QPointF(x_offset + x_distance_from_top + 0,
                             y_offset + self.box_height / 5)
        right_point = QPointF(x_offset - x_distance_from_top + self.box_width,
                              y_offset + self.box_height / 5)
        bottom_middle_point = QPointF(x_offset + self.box_width / 2,
                                      y_offset + (self.box_height / 5) * 2)

        left_polygon = QPolygonF()
        left_polygon << left_point \
                     << left_point + QPointF(0, height) \
                     << bottom_middle_point + QPointF(0, height) \
                     << bottom_middle_point \
                     << left_point
        path.addPolygon(left_polygon)

        right_polygon = QPolygonF()
        right_polygon << right_point \
                      << right_point + QPointF(0, height) \
                      << bottom_middle_point + QPointF(0, height) \
                      << bottom_middle_point \
                      << right_point
        path.addPolygon(right_polygon)

        return path

    def createBottomInsidePath(self) -> QPainterPath:
        """
        Creates the path for the bottom part of the box that is seen from inside.
        This is its own method to not clutter the paintEvent method.
        """
        path = QPainterPath()

        x_offset = self.box_offset.x()
        y_offset = self.box_offset.y()
        x_distance_from_top = 2

        left_point = QPointF(x_offset + x_distance_from_top + 0,
                             y_offset + self.box_height / 5)
        right_point = QPointF(x_offset - x_distance_from_top + self.box_width,
                              y_offset + self.box_height / 5)
        top_middle_point = QPointF(x_offset + self.box_width / 2,
                                   y_offset + 0)
        bottom_middle_point = QPointF(x_offset + self.box_width / 2,
                                      y_offset + (self.box_height / 5) * 2)

        top_polygon = QPolygonF()
        top_polygon << top_middle_point \
                    << right_point \
                    << bottom_middle_point \
                    << left_point \
                    << top_middle_point
        path.addPolygon(top_polygon)

        return path

    @pyqtProperty(QPointF)
    def box_offset(self) -> QPointF:
        return self._box_offset

    @box_offset.setter
    def box_offset(self, pos: QPointF) -> None:
        self._box_offset = pos
        self.update()

    @pyqtProperty(QPointF)
    def top_offset(self) -> QPointF:
        return self._top_offset

    @top_offset.setter
    def top_offset(self, pos: QPointF) -> None:
        self._top_offset = pos
        self.update()

    @pyqtProperty(float)
    def top_opacity(self) -> float:
        return self._top_opacity

    @top_opacity.setter
    def top_opacity(self, opacity: float) -> None:
        self._top_opacity = opacity
        self.update()
