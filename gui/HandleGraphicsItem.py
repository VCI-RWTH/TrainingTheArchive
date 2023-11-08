from typing import Dict, Any, Optional

from PyQt6.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem, QWidget, QGraphicsSceneMouseEvent, QGraphicsDropShadowEffect, QMenu, QGraphicsSceneContextMenuEvent
from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSlot
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QPainterPath, QIcon

TOP_LEFT = 0
TOP_RIGHT = 1
BOTTOM_RIGHT = 2
BOTTOM_LEFT = 3


class HandleGraphicsItem(QGraphicsItem):
    """
    Base class for a graphics item that can be resized by handles e.g. Notes, Groups or ImageGraphicsItem.
    Classes that inherit from this class have a handle at each corner that can be used to resize the item.
    However, the item will always be a rectangle.
    """

    default_size = 200

    def __init__(self):
        super().__init__()

        # Set pen and brush (style)
        self.pen = QPen(Qt.GlobalColor.black, 5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        self.brush = QBrush(Qt.BrushStyle.NoBrush)

        # Make the item movable and selectable
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setCursor(Qt.CursorShape.SizeAllCursor)

        # Create handles
        self.handles = []
        for position in [TOP_LEFT, TOP_RIGHT, BOTTOM_RIGHT, BOTTOM_LEFT]:
            self.handles.append(Handle(position, self))

        # Move handles into (default) position
        self.handles[TOP_LEFT].setPos(0, 0)
        self.handles[TOP_RIGHT].setPos(self.default_size, 0)
        self.handles[BOTTOM_RIGHT].setPos(self.default_size, self.default_size)
        self.handles[BOTTOM_LEFT].setPos(0, self.default_size)

        # Create the drop shadow effect used when the item is selected
        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(20)
        self.shadow.setOffset(0, 0)
        self.shadow.setColor(Qt.GlobalColor.darkGray)
        self.shadow.setEnabled(False)
        self.setGraphicsEffect(self.shadow)

        # Variable to store the position a move action started
        # This is used to determine whether the item has been moved or not, to avoid filling the entire history with
        # move actions when the user just clicks on the item
        self.move_start_pos: QPointF = None

        self.initContextMenu()

    def initContextMenu(self) -> None:
        """
        Creates the context menu (right click menu) for the item.
        As a base class the only action is to remove the item.
        """
        self.context_menu = QMenu()

        remove_action = self.context_menu.addAction(QIcon(''), 'Remove')
        remove_action.triggered.connect(self.remove)

    def contextMenuEvent(self, event: QGraphicsSceneContextMenuEvent) -> None:
        self.context_menu.exec(event.screenPos())

        super().contextMenuEvent(event)

    def boundingRect(self) -> QRectF:
        """
        Return the bounding rectangle of the item.
        The bounding rect only contains the rectangle of the item.
        Therefore, it does not contain the all the handles completely.

        :return: The bounding rectangle of the item
        """
        return QRectF(self.handles[TOP_LEFT].getCenter(), self.handles[BOTTOM_RIGHT].getCenter())

    def shape(self) -> QPainterPath:
        """
        Return the shape of the item.
        For this base class the shape is just the bounding rectangle.
        However, for classes that inherit from this class the shape can be more complex.

        :return: The bounding rectangle of the item as a QPainterPath
        """
        path = QPainterPath()
        path.addRect(self.boundingRect())

        return path

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: Optional[QWidget] = ...) -> None:
        """
        Override the paint method, to paint the items bounding rect.
        This method is mainly for debugging because only classes that inherit from this class should actually be used
        and added to the canvas.
        """
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.setPen(self.pen)
        painter.setBrush(self.brush)

        painter.drawRect(self.boundingRect())

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value: Any) -> Any:
        """
        Override the itemChange method to enable the drop shadow when the item is selected.
        """
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedChange:
            self.shadow.setEnabled(value)

        return super().itemChange(change, value)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """
        Override the mousePressEvent to store the position the move action started, to later determine whether
        the item has been moved or not.
        """
        self.move_start_pos = self.pos()

        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """
        Override the mouseReleaseEvent to determine whether the item has been moved or not and notify the scene.
        """
        if abs(self.pos().x() - self.move_start_pos.x()) > 10 or abs(self.pos().y() - self.move_start_pos.y()) > 10:
            self.scene().itemMoved(self)

        super().mouseReleaseEvent(event)

    def handlePressed(self, position: int, event: QGraphicsSceneMouseEvent) -> None:
        """
        This method is called when a handle is pressed and the item is about to be resized.
        The default implementation does nothing and can be overridden by classes that inherit from this class.

        :param position: The position of the handle, that was pressed (TOP_LEFT, TOP_RIGHT, BOTTOM_RIGHT, BOTTOM_LEFT)
        :param event: The mouse event of the handle, that triggered the handle press
        """
        pass

    def handleMoving(self, position: int, event: QGraphicsSceneMouseEvent) -> None:
        """
        This method is called when a handle is moved and the item is being resized.
        In the default implementation only the other handles are moved to keep the item a rectangle.

        :param position: The position of the handle, that was moved (TOP_LEFT, TOP_RIGHT, BOTTOM_RIGHT, BOTTOM_LEFT)
        :param event: The mouse event of the handle, that triggered the handle move
        """
        handle = self.handles[position]

        # Move Handles
        if position == TOP_LEFT:
            self.handles[BOTTOM_LEFT].setX(handle.x())
            self.handles[TOP_RIGHT].setY(handle.y())
        elif position == TOP_RIGHT:
            self.handles[BOTTOM_RIGHT].setX(handle.x())
            self.handles[TOP_LEFT].setY(handle.y())
        elif position == BOTTOM_RIGHT:
            self.handles[TOP_RIGHT].setX(handle.x())
            self.handles[BOTTOM_LEFT].setY(handle.y())
        elif position == BOTTOM_LEFT:
            self.handles[TOP_LEFT].setX(handle.x())
            self.handles[BOTTOM_RIGHT].setY(handle.y())

        self.scene().update()

    def handleReleased(self, position: int, event: QGraphicsSceneMouseEvent) -> None:
        """
        This method is called when a handle is released and the item has been resized.
        The default implementation only normalizes the handles and notifies the scene.

        :param position: The position of the handle, that was moved (TOP_LEFT, TOP_RIGHT, BOTTOM_RIGHT, BOTTOM_LEFT)
        :param event: The mouse event of the handle, that triggered the handle move
        """
        self.normalizeHandles()

        if self.scene():
            self.scene().itemScaled(self)

    def normalizeHandles(self) -> None:
        """
        Normalize the handles, so that the TOP_LEFT handle is at (0, 0) and the BOTTOM_RIGHT handle is in the
        bottom right corner of the item.
        This needs to be called after the item has been resized, since the handles are moved freely when the item is resized
        """
        # Get all the handle coordinates
        handles_x = [handle.x() for handle in self.handles]
        handles_y = [handle.y() for handle in self.handles]

        # Calculate maximum and minimum coordinates
        min_x = min(handles_x)
        min_y = min(handles_y)
        max_x = max(handles_x)
        max_y = max(handles_y)

        # Move handles so that TOP_LEFT is at (0, 0)
        self.handles[TOP_LEFT].setPos(0, 0)
        self.handles[TOP_RIGHT].setPos(max_x - min_x, 0)
        self.handles[BOTTOM_RIGHT].setPos(max_x - min_x, max_y - min_y)
        self.handles[BOTTOM_LEFT].setPos(0, max_y - min_y)

        # Move entire item to adjust for the new handle positions
        self.moveBy(min_x, min_y)

        if self.scene():
            self.scene().update()

    @pyqtSlot()
    def remove(self) -> None:
        """
        Remove the item from the scene. Without updating anything else.
        This method should be overridden by classes that inherit from this class to properly remove the item from the
        scene.
        """
        if self.scene():
            self.scene().removeItem(self)

    def setHandlesVisible(self, visible: bool) -> None:
        """
        Makes the handles visible or invisible.

        :param visible: Whether the handles should be visible or not
        """
        for handle in self.handles:
            handle.brush = QBrush(Qt.GlobalColor.black) if visible else QBrush(Qt.BrushStyle.NoBrush)

    def setHandleColor(self, color: QColor) -> None:
        """
        Sets the color of the handles.

        :param color: The color the handles should have
        """
        for handle in self.handles:
            handle.brush = QBrush(color)

    def getHandleSize(self) -> int:
        return self.handles[TOP_LEFT].size

    def getWidth(self) -> float:
        return abs(self.handles[BOTTOM_RIGHT].x() - self.handles[TOP_LEFT].x())

    def getHeight(self) -> float:
        return abs(self.handles[BOTTOM_RIGHT].y() - self.handles[TOP_LEFT].y())

    def checkForGroupNameOverlap(self) -> None:
        """
        Checks whether the item is overlapping with a group name.
        If it is overlapping, the item is pushed away from the group name.
        """
        # Get the bounding rect of the item in scene space
        bounding_rect_scene_space = QRectF(self.mapToScene(QPointF(0, 0)),
                                           self.mapToScene(QPointF(self.getWidth(), self.getHeight())))

        for group in self.scene().getGroups():
            # Get the bounding rect of the group name in scene space
            group_name_rect = QRectF(group.group_name.scenePos(),
                                     group.group_name.scenePos() + QPointF(group.group_name.boundingRect().width(),
                                                                           group.group_name.boundingRect().height()))

            # Check if the item is overlapping with the group name
            if bounding_rect_scene_space.intersects(group_name_rect):
                # The Image is overlapping with the group name
                # Determine in which direction the item should be pushed to not overlap with the group name

                # Determine the distances the item has to be pushed into each direction
                distance_right = abs(bounding_rect_scene_space.left() - group_name_rect.right())
                distance_left = abs(bounding_rect_scene_space.right() - group_name_rect.left())
                distance_up = abs(bounding_rect_scene_space.bottom() - group_name_rect.top())
                distance_down = abs(bounding_rect_scene_space.top() - group_name_rect.bottom())

                # Determine the minimum distance
                min_distance = min(distance_right, distance_left, distance_up, distance_down)

                # Push the item into the direction of the minimum distance
                if min_distance == distance_right:
                    self.moveBy(distance_right - self.getHandleSize() // 2, 0)
                elif min_distance == distance_left:
                    self.moveBy(-distance_left - self.getHandleSize() // 2, 0)
                elif min_distance == distance_up:
                    self.moveBy(0, -distance_up - self.getHandleSize() // 2)
                elif min_distance == distance_down:
                    self.moveBy(0, distance_down - self.getHandleSize() // 2)

    def serialize(self) -> Dict[str, Any]:
        return {
            'x': self.x(),
            'y': self.y(),
            'bottom_right': self.handles[BOTTOM_RIGHT].serialize()
        }


class Handle(QGraphicsItem):
    """
    A Handle at the corner of a HandleGraphicsItem that can be used to resize the parent item.
    """

    size: int = 20

    pen = Qt.PenStyle.NoPen
    brush = QBrush(Qt.GlobalColor.black)

    def __init__(self, position: int, parent: HandleGraphicsItem):
        super().__init__(parent)

        # Make the handle movable
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)

        self.setZValue(self.parentItem().zValue() + 1)

        # Set the correct cursor when hovering over the handle
        self.position = position
        if self.position is TOP_LEFT or self.position is BOTTOM_RIGHT:
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif self.position is TOP_RIGHT or self.position is BOTTOM_LEFT:
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self.size, self.size)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: Optional[QWidget] = ...) -> None:
        # Configure the painter
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.setPen(self.pen)
        painter.setBrush(self.brush)

        # Reduce the size of the bounding rect by half the size of the handle to make the handles appearance smaller
        bounding_rect = self.boundingRect()

        width = bounding_rect.width() // 2
        height = bounding_rect.height() // 2

        draw_rect = QRectF(width // 2, height // 2, width, height)

        painter.drawRect(draw_rect)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """
        Override the mousePressEvent to call the handlePressed method of the parent item.
        """
        if self.parentItem():
            self.parentItem().handlePressed(self.position, event)

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """
        Override the mouseMoveEvent to call the handleMoving method of the parent item.
        """
        if self.parentItem():
            self.parentItem().handleMoving(self.position, event)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """
        Override the mouseReleaseEvent to call the handleReleased method of the parent item.
        """
        if self.parentItem():
            self.parentItem().handleReleased(self.position, event)

        super().mouseReleaseEvent(event)

    def getCenter(self) -> QPointF:
        return self.pos() + QPointF(self.size / 2, self.size / 2)

    def getSize(self) -> int:
        return self.size

    def serialize(self) -> Dict[str, float]:
        return {
            'x': self.x(),
            'y': self.y()
        }

    def deserialize(self, data: Dict[str, float]) -> None:
        self.setPos(data['x'], data['y'])
