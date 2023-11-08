from typing import List, Dict, Any, Optional

from PyQt6.QtWidgets import QMenu, QGraphicsTextItem, QGraphicsSceneMouseEvent, QColorDialog, QStyleOptionGraphicsItem
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QPen, QPainterPath, QIcon, QPixmap, QFont, QFontMetricsF, QKeyEvent, QFocusEvent

from gui.Colors import *
from gui.HandleGraphicsItem import *
from gui.ImageGraphicsItem import ImageGraphicsItem
from gui.Note import Note


class Group(HandleGraphicsItem):
    """
    A group on the canvas that can group multiple items on the canvas together.
    Each group has a corresponding group in the artsearch class to keep track of the items in the group and update the search.
    """
    def __init__(self):
        super().__init__()

        self.pen = QPen(Qt.GlobalColor.black, 2, Qt.PenStyle.DashLine)
        self.setZValue(2 + 9999)  # Groups should always be on top of everything else to see their border

        # Create the group name text item and set its parent to the top left corner to make it move with the corner
        self.group_name = GroupName(self.handles[TOP_LEFT])
        self.group_name.setPos(QPointF(self.getHandleSize() // 2, self.getHandleSize() // 2))
        self.group_name.setText('New Group')

        # These lists keep track of which items should be moved and scaled with the group
        # This is necessary because the process of moving and scaling is split up into multiple events
        # (Press, Move, Release)
        # For scale_items the relative position of the item to the group is also stored
        self.move_items: [QGraphicsItem] = []
        self.scale_items: [(QGraphicsItem, QPointF)] = []

        self.initContextMenu()

    def initContextMenu(self) -> None:
        """
        Expands the base context menu with the option to change the color of the group.
        """
        super().initContextMenu()

        color_menu = self.context_menu.addMenu('Change Color')

        # Simple function to add a color option to the color menu
        def addColor(color: QColor, name: str):
            pixmap = QPixmap(20, 20)
            pixmap.fill(color)
            action = color_menu.addAction(QIcon(pixmap), name)
            action.triggered.connect(lambda: self.setColor(color))

        addColor(QColor(BLACK), 'Black')
        addColor(QColor(RED), 'Red')
        addColor(QColor(GREEN), 'Green')
        addColor(QColor(BLUE), 'Blue')

        custom_action = color_menu.addAction(QIcon(''), 'Custom')
        custom_action.triggered.connect(self.setCustomColor)

    def shape(self) -> QPainterPath:
        """
        Override the shape function to include the handles in the shape because the handles are visible for groups.
        and remove the inside of the group from the shape.
        This is done so that the group can be selected by clicking on the border of the group.
        Otherwise, the items in the group would not be selectable because the group would be selected instead.
        """
        path = QPainterPath()
        path.addRect(QRectF(self.handles[TOP_LEFT].pos(),
                            self.handles[BOTTOM_RIGHT].pos() + QPointF(self.getHandleSize(), self.getHandleSize())))

        # Subtract the inside of the group from the shape
        subtract = QPainterPath()
        subtract.addRect(QRectF(self.handles[TOP_LEFT].pos() + QPointF(self.getHandleSize(), self.getHandleSize()),
                                self.handles[BOTTOM_RIGHT].pos()))

        return path.subtracted(subtract)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """
        Override the mousePressEvent to keep track of which items should be moved with the group.
        """
        if event.button() == Qt.MouseButton.LeftButton and event.modifiers() != Qt.KeyboardModifier.ShiftModifier:
            self.move_items = self.getContent()

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """
        Override the mouseMoveEvent to move the items in the group that should be moved with the group.
        """
        if event.buttons() == Qt.MouseButton.LeftButton:
            # Determine the amount the group has been moved
            diff = event.pos() - event.lastPos()

            # Move all the items in the group
            for item in self.move_items:
                item.moveBy(diff.x(), diff.y())

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """
        Override the mouseReleaseEvent to reset the list of items that should be moved with the group
        when one move action is finished
        """
        if event.button() == Qt.MouseButton.LeftButton:
            self.move_items = []

        super().mouseReleaseEvent(event)

    def handlePressed(self, position: int, event: QGraphicsSceneMouseEvent) -> None:
        """
        Override handlePressed to determine which items should be scaled with the group.
        """
        super().handlePressed(position, event)

        # Determine which items should be scaled with the group and their relative position to the group
        if event.button() == Qt.MouseButton.LeftButton and event.modifiers() == Qt.KeyboardModifier.ShiftModifier:
            for item in self.getContent():
                relative_position = item.pos() - self.mapToScene(self.handles[TOP_LEFT].pos())
                relative_position_percentage = QPointF(relative_position.x() / self.getWidth(),
                                                       relative_position.y() / self.getHeight())

                self.scale_items.append((item, relative_position_percentage))

    def handleMoving(self, position: int, event: QGraphicsSceneMouseEvent) -> None:
        """
        Override handleMoving to scale the items that should be scaled with the group.
        Keeping their relative position to the group the same.
        """
        super().handleMoving(position, event)

        # Scale the items that should be scaled with the group
        if event.buttons() == Qt.MouseButton.LeftButton:
            # Determine the amount the group has been scaled
            diff = event.pos() - event.lastPos()

            # Adjust the amount the group has been scaled based on which handle has been moved
            # For example when the top left corner is moved to the bottom left everything get smaller,
            # but when the bottom right corner is moved to the bottom left everything gets bigger
            if position == TOP_LEFT:
                diff = -diff
            elif position == TOP_RIGHT:
                diff = QPointF(diff.x(), -diff.y())
            elif position == BOTTOM_RIGHT:
                diff = diff
            elif position == BOTTOM_LEFT:
                diff = QPointF(-diff.x(), diff.y())

            for item, relative_position_percentage in self.scale_items:

                # Calculate new absolute position based on the relative position to the group
                pos = self.mapToScene(self.handles[TOP_LEFT].pos())
                pos += QPointF(relative_position_percentage.x() * self.getWidth() + diff.x(),
                               relative_position_percentage.y() * self.getHeight() + diff.y())

                item.setPos(pos)

                # Calculate new size
                ratio = QPointF(self.getWidth() / (self.getWidth() - diff.x()),
                                self.getHeight() / (self.getHeight() - diff.y()))

                item.handles[BOTTOM_RIGHT].setPos(item.handles[BOTTOM_RIGHT].pos().x() * ratio.x(),
                                                  item.handles[BOTTOM_RIGHT].pos().y() * ratio.y())

                item.handleMoving(BOTTOM_RIGHT, event)

        # Update the text size of the group name when the group is scaled
        self.group_name.updateSize()

    def handleReleased(self, position: int, event: QGraphicsSceneMouseEvent) -> None:
        """
        Override handleReleased to clear the list of items that should be scaled with the group.
        And notify all the scaled items, that the scaling is finished.
        """
        super().handleReleased(position, event)

        # Clear the list of items that should be scaled with the group
        if event.button() == Qt.MouseButton.LeftButton:
            # Call the handleReleased/scaling finished functions for all the items that were scaled with the group
            for item, _ in self.scale_items:
                item.handleReleased(position, event)

            self.scale_items = []

    def getContent(self) -> List[QGraphicsItem]:
        """
        Returns all the items that the group fully contains
        :return: List of items that the group fully contains
        """
        content = []

        # Go through all the items in the scene and check if they are inside the group
        group_mapped_bounding_rect = self.mapRectToScene(self.boundingRect())
        for item in self.scene().items(group_mapped_bounding_rect, mode=Qt.ItemSelectionMode.ContainsItemBoundingRect):
            if item is self:
                continue
            if isinstance(item, Group) or isinstance(item, ImageGraphicsItem) or isinstance(item, Note):
                content.append(item)

        return content

    def getImages(self) -> List[ImageGraphicsItem]:
        """
        Returns all the images that the group fully contains, by filtering the content of the group
        :return: List of images that the group fully contains
        """
        images = []

        for item in self.getContent():
            if isinstance(item, ImageGraphicsItem):
                images.append(item)

        return images

    def remove(self) -> None:
        """
        Override remove to remove the group properly from the scene
        """
        if self.scene():
            self.scene().removeGroup(self)


    def setColor(self, color) -> None:
        if isinstance(color, str):
            color = QColor(color)

        self.pen.setColor(color)
        self.setHandleColor(color)

    def setCustomColor(self) -> None:
        """
        Opens a QColorDialog to set a custom color for the group
        """
        color = QColorDialog.getColor(self.pen.color())
        if color.isValid():
            self.setColor(color)

    def setName(self, name: str) -> None:
        self.group_name.setText(name)

    def getName(self) -> str:
        """
        This function is a more convenient way to get the name of the group

        :return: The name of the group
        """
        return self.group_name.getText()

    def serialize(self) -> Dict[str, Any]:
        super_dict = super().serialize()

        super_dict['name'] = self.getName()
        super_dict['color'] = self.pen.color().name()

        return super_dict


class GroupName(QGraphicsTextItem):
    """
    This class is the name of the group that is displayed in the top corner of the group
    """

    def __init__(self, parent: Group):
        super().__init__(parent)

        self.text = 'self.toPlainText()'  # The text that is displayed, initial value is not important
        self.font = self.font()

        # Set some flags to make the text behave like a normal text editor
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextEditorInteraction)
        self.setCursor(Qt.CursorShape.IBeamCursor)
        self.setZValue(self.parentItem().zValue() + 1)

        self.pen = QPen(Qt.GlobalColor.black, 2, Qt.PenStyle.SolidLine)
        self.brush = QBrush(Qt.GlobalColor.white)

        self.updateSize()

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self.parentItem().parentItem().getWidth(),
                            self.parentItem().parentItem().getHeight() * 0.2)

    def shape(self) -> QPainterPath:
        """
        Override the shape method to make the text editable by clicking anywhere in the bounding rect
        instead of only the text
        """
        path = QPainterPath()
        path.addRect(self.boundingRect())

        return path

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: Optional[QWidget] = ...) -> Any:
        painter.setPen(self.pen)
        painter.setBrush(self.brush)

        painter.drawLine(self.boundingRect().bottomLeft(), self.boundingRect().bottomRight())

        super().paint(painter, option, widget)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """
        Override mousePressEvent to clear the text when the user clicks on the text for the first time
        """
        if event.button() == Qt.MouseButton.LeftButton:
            if self.toPlainText() == 'New Group':
                # If the text is the default text, clear it
                self.setPlainText('')
            else:
                # Do this to show the full text if the processed text with "..." is shown
                self.setPlainText(self.text)

        super().mousePressEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """
        Override keyPressEvent to store the new text when the user changes it
        """
        super().keyPressEvent(event)

        # Store the new text
        self.text = self.toPlainText()

    def focusOutEvent(self, event: QFocusEvent) -> None:
        """
        Override the focus event to update the size of the text when the user is done editing it.
        This is done because when updating it is checked if the text is too long and if it is,
        the displayed text is shortened while storing the full text.
        """
        self.updateSize()

        super().focusOutEvent(event)

    def setText(self, text: str):
        self.text = text
        self.updateSize()

    def getText(self) -> str:
        return self.text

    def updateSize(self) -> None:
        """
        Update the size of the text and shorten it if it is too long.
        This is called whenever the text changes or the group is resized
        :return:
        """
        # Set the font size to half of the height of the bounding rect
        self.font.setPixelSize(int(self.boundingRect().height() // 2))

        metrics = QFontMetricsF(self.font)
        # Check if the is longer than the width of the bounding rect
        if metrics.horizontalAdvance(self.text) > self.boundingRect().width():
            # If it is, shorten the text and add '...' at the end
            processed_text = self.text
            processed_text = processed_text[:int(self.boundingRect().width() / metrics.averageCharWidth())]
            processed_text = processed_text[:-3] + '...'

            self.setPlainText(processed_text)
        else:
            # Since updateSize is called when the text is changed, the text is set to the full text if it fits
            self.setPlainText(self.text)

        # Update the font (size)
        self.setFont(self.font)
