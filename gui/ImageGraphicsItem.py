import os
from typing import Dict, Any

from PyQt6.QtWidgets import QWidget, QGraphicsSceneMouseEvent, QStyleOptionGraphicsItem, QApplication
from PyQt6.QtCore import Qt, QRectF, QPointF, QSize
from PyQt6.QtGui import QPainter, QPixmap, QAction, QIcon, QFocusEvent

from gui.HandleGraphicsItem import *
from gui.ImageWidget import ImageWidgetSearchBar
from gui.PreviewWindow import PreviewWindow
from gui.SearchInput import SearchBarLineEdit
from gui.Util import svgToQImage

BASE_PATH = os.path.dirname(__file__)


class ImageGraphicsItem(HandleGraphicsItem):
    """
    A graphics item to display an image in a graphics scene (the canvas).
    Each image that is on the canvas has to have a positive weight for the search.
    Therefore, an image should only be added by calling the "addImage" method of the CanvasScene,
    where the necessary adjustments are made.
    """
    def __init__(self, id: int, path: str, artsearch):
        # Set id before parent constructor because initContextMenu is called in the parent constructor
        # and the id is needed there
        self.id = id
        super().__init__()

        self.artsearch = artsearch

        self.path = path
        self.pixmap = QPixmap(path)
        self.pixmap_pos = self.handles[TOP_LEFT].getCenter()  # The relative position of the pixmap to the graphics item
        self.pixmap_scaled = self.pixmap.scaled(int(self.getWidth()), int(self.getHeight()),  # The pixmap scaled to the
                                                Qt.AspectRatioMode.KeepAspectRatio)           # current size of the graphics item
        self.placeHandles()  # Place the handles on the corners of the image

        # Stores whether the image is marked as a favorite
        # Favorites do not affect the search they are only for organization purposes and marked by a star in the top right corner
        self.favorite = False
        self.favorite_pixmap = QPixmap.fromImage(svgToQImage(os.path.join(BASE_PATH, 'icons', 'StarIconWithBorder.svg'), QSize(100, 100)))

        self.setHandlesVisible(False)
        self.setZValue(0)

    def initContextMenu(self) -> None:
        super().initContextMenu()

        self.favorite_action = QAction('Favorite')
        self.favorite_action.triggered.connect(self.favorite)
        self.context_menu.insertAction(self.context_menu.actions()[0], self.favorite_action)

        # Action to use the image as the search prompt
        search_action = self.context_menu.addAction('Search for Image')
        search_action.triggered.connect(lambda: self.scene().search_bar.imageSearch(self.path))

        # Put the image back into the search bar
        if self.id != -1:
            self.put_back_action = QAction('Put Back')
            self.put_back_action.triggered.connect(self.putBack)
            self.context_menu.insertAction(self.context_menu.actions()[0], self.put_back_action)

        # Preview the image in a separate window
        self.preview_action = QAction('Show Preview')
        self.preview_action.triggered.connect(self.preview)
        self.context_menu.insertAction(self.context_menu.actions()[0], self.preview_action)

    def boundingRect(self) -> QRectF:
        return QRectF(self.getHandleSize() // 2, self.getHandleSize() // 2,
                      self.pixmap_scaled.width(), self.pixmap_scaled.height())

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: Optional[QWidget] = ...) -> None:
        """
        Overwrite the paint method to draw the pixmap and the favorite star
        """
        # Draw the correctly scaled pixmap
        painter.drawPixmap(self.pixmap_pos, self.pixmap_scaled)

        # Draw the favorite star if the image is marked as favorite
        if self.favorite:
            size = self.pixmap_scaled.width() + self.pixmap_scaled.height()
            size /= 10
            size = int(size)

            favorite_pixmap_scaled = QPixmap.fromImage(svgToQImage(os.path.join(BASE_PATH, 'icons', 'StarIconWithBorder.svg'),
                                                                   QSize(size, size)))

            # Place the star in the top right corner of the pixmap
            favorite_pixmap_pos = QPointF(self.pixmap_pos.x(), self.pixmap_pos.y())
            favorite_pixmap_pos -= QPointF(favorite_pixmap_scaled.width() / 2, favorite_pixmap_scaled.height() / 2)
            favorite_pixmap_pos += QPointF(self.pixmap_scaled.width(), 0)

            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.drawPixmap(favorite_pixmap_pos, favorite_pixmap_scaled)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """
        Update the preview window when the image is clicked (if it is visible)
        """
        super().mousePressEvent(event)

        if self.scene() and self.scene().preview_window.isVisible():
            self.scene().preview_window.setImage(self.id, self.path)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """
        Check where the image was dropped.
        If it was dropped on the search input, use it for image search.
        If it was dropped anywhere else on search bar, remove it and reset its weight.
        """
        super().mouseReleaseEvent(event)

        # Prevent the image from overlapping with a group name
        self.checkForGroupNameOverlap()

        # Create variables to improve readability
        scene = self.scene()
        view = scene.views()[0]

        pos_viewport_space = view.mapFromScene(event.scenePos())
        pos_global_space = view.mapToGlobal(pos_viewport_space)

        # Get the widget that the image was dropped on
        widget = QApplication.widgetAt(pos_global_space)

        if isinstance(widget, SearchBarLineEdit):
            # If the image is dropped on the search input, use it for image search
            if abs(self.pos().x() - self.move_start_pos.x()) > 10 or abs(self.pos().y() - self.move_start_pos.y()) > 10:
                # Remove the time stamp of the image moving, because it will be removed
                # This has to be done because we have to call the parent method first which creates the timestamp
                scene.history.popTimeStamp()

            self.setPos(self.move_start_pos)  # Move the image back to its original position
            scene.search_bar.imageSearch(self.path)

        elif isinstance(widget, QWidget):
            remove = False

            # Recursively check if the widget is a child of the search bar
            while widget.parent():
                if scene.search_bar == widget:
                    remove = True
                    break

                widget = widget.parent()

            # If the image is dropped on the search bar, remove it
            if remove:
                if abs(self.pos().x() - self.move_start_pos.x()) > 10 or abs(self.pos().y() - self.move_start_pos.y()) > 10:
                    # Remove the time stamp of the image moving, because it will be removed
                    # This has to be done because we have to call the parent method first which creates the timestamp
                    scene.history.popTimeStamp()

                scene.artsearch.setImageNeutral(self.id)
                scene.removeItem(self)
                scene.search_bar.updateResults()
                scene.history.addTimeStamp()

    def handleMoving(self, position: int, event: QGraphicsSceneMouseEvent) -> None:
        """
        This is called during the resizing.
        In this function the pixmap is anchored according to the handle that is being dragged.
        For example if the top left handle is dragged, the pixmap is anchored to the bottom right corner.
        but if the bottom right handle is dragged, the pixmap is anchored to the top left corner.
        """
        super().handleMoving(position, event)

        # Rescale the pixmap to the new size
        self.updatePixmapSize()

        # Anchor the pixmap to the opposite corner of the handle that is being dragged
        if position == TOP_LEFT:
            self.pixmap_pos = self.handles[BOTTOM_RIGHT].getCenter() - QPointF(self.pixmap_scaled.width(),
                                                                               self.pixmap_scaled.height())
        elif position == TOP_RIGHT:
            self.pixmap_pos = QPointF(self.handles[TOP_LEFT].getCenter().x(),
                                      self.handles[BOTTOM_RIGHT].getCenter().y() - self.pixmap_scaled.height())
        elif position == BOTTOM_RIGHT:
            self.pixmap_pos = self.handles[TOP_LEFT].getCenter()
        elif position == BOTTOM_LEFT:
            self.pixmap_pos = QPointF(self.handles[BOTTOM_RIGHT].getCenter().x() - self.pixmap_scaled.width(),
                                      self.handles[TOP_LEFT].getCenter().y())

    def handleReleased(self, position: int, event: QGraphicsSceneMouseEvent) -> None:
        """
        When the item is resized place the handles again since the item can be resized freely but the image has a
        fixed aspect ratio.
        Also readjust the position of the pixmap to the top left corner of the item since it can be moved away from it
        when resized.
        """
        self.placeHandles()
        super().handleReleased(position, event)
        self.pixmap_pos = self.handles[TOP_LEFT].getCenter()

    def itemChange(self, change: QGraphicsItem.GraphicsItemChange, value: Any) -> Any:
        """
        Overwrite this method to ensure that the selected image is always on top of the other images
        """
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged and value:
            # Move image to top
            self.setZValue(0)

            # Move all other images one layer down
            for image in self.scene().getImages():
                if image is self:
                    continue

                image.setZValue(image.zValue() - 1)

        return super().itemChange(change, value)

    def placeHandles(self) -> None:
        """
        Places the handles at the corners of pixmap. This is called when the image is moved or resized, since the
        item can be resized freely but the image has a fixed aspect ratio.
        """
        top_left = self.pixmap_pos - QPointF(self.getHandleSize() / 2, self.getHandleSize() / 2)

        self.handles[TOP_LEFT].setPos(top_left)
        self.handles[TOP_RIGHT].setPos(top_left + QPointF(self.pixmap_scaled.width(), 0))
        self.handles[BOTTOM_RIGHT].setPos(top_left + QPointF(self.pixmap_scaled.width(), self.pixmap_scaled.height()))
        self.handles[BOTTOM_LEFT].setPos(top_left + QPointF(0, self.pixmap_scaled.height()))

    def updatePixmapSize(self) -> None:
        """
        Updates the size of the pixmap to match the size of the bounding rect
        """
        self.pixmap_scaled = self.pixmap.scaled(int(self.getWidth()), int(self.getHeight()),
                                                Qt.AspectRatioMode.KeepAspectRatio)

    def remove(self) -> None:
        """
        Removes the image from the canvas and puts it in the box (negative weight).
        Since custom images don't have a weight they are just removed
        """
        if self.scene():
            if self.id != -1:
                # Put image in box and update search
                self.scene().removeImage(self)
            else:
                # Just delete image
                self.scene().removeItem(self)

    def favorite(self) -> None:
        self.favorite = not self.favorite
        self.scene().update()

    def putBack(self) -> None:
        """
        Removes the image from the canvas but does not put it in the box (negative weight).
        Instead, it is just removed and its weight is set to neutral.
        """
        # Store the scene because after removing the item, it is None
        scene = self.scene()
        if scene:
            scene.removeItem(self)
            scene.artsearch.setImageNeutral(self.id)

            scene.update()
            scene.search_bar.updateResults()

            scene.history.addTimeStamp()

    def preview(self) -> None:
        """
        Shows the preview window with the image.
        If the preview window is already open, it is only is updated and the show() is redundant.
        """
        if self.scene():
            self.scene().preview_window.setImage(self.id, self.path)
            self.scene().preview_window.show()

    def serialize(self) -> Dict[str, Any]:
        super_dict = super().serialize()

        super_dict["id"] = self.id
        super_dict["path"] = self.path
        super_dict["favorite"] = self.favorite
        super_dict["z_value"] = self.zValue()

        return super_dict
