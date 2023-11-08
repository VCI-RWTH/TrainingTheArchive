import sys
import os
from typing import Tuple

from PyQt6.QtWidgets import QGraphicsView, QSlider, QPushButton, QVBoxLayout, QHBoxLayout, QSizePolicy
from PyQt6.QtCore import Qt, QEvent, pyqtSlot
from PyQt6.QtGui import QTransform, QWheelEvent, QNativeGestureEvent, QMouseEvent, QIcon, QKeyEvent

from gui.CanvasScene import CanvasScene

base_path = os.path.dirname(__file__)


class CanvasView(QGraphicsView):
    """
    This class is the view in which the canvas (GraphicsScene) is displayed.
    It is responsible for navigating the scene (zooming, panning, ...).

    Note that a pinching gesture emits a QNativeGestureEvent on macOS, but a QWheelEvent on Windows.
    So both cases have to be handled separately.
    """
    def __init__(self):
        super().__init__()

        # Zoom settings
        self._zoom: int = 10                       # Stores the current zoom level
        self.zoom_factor: float = 1.25             # How much the zoom changes when zooming in or out one step
        self.zoom_range: Tuple[int, int] = (1, 10) # The range of zoom levels
        self.zoom_clamp: bool = True               # Whether to clamp the zoom to the zoom range or not
        self.freeze: bool = False                  # Whether to freeze the zoom (disable zooming) or not

        # Since we zoom out to the full scene when the user double clicks we have to store the transformations used
        # to zoom out, to be able to zoom back in to the same position
        self.current_transform = None
        self.current_center = None

        # These variables are only used on macOS
        # since the event is emitted way too often to reduce/increase by one level each time.
        # Instead, we accumulate the "pinch amount" in the counter and zoom when it reaches a certain threshold.
        if sys.platform == 'darwin':
            self.zoom_value_counter: float = 0
            self.zoom_value_threshold: float = 0.1

        self.zoom = 5

        # Call functions to set up the UI and the (scrollbar) policies
        self.initUI()
        self.initPolicies()

    def initUI(self) -> None:
        # Set the drag mode to be able to drag the scene around to navigate it
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)

        # Create the actual scene (canvas) and display it in the view
        self.setScene(CanvasScene())

    def initPolicies(self) -> None:
        """
        Sets tje scrollbar policies to never display the scrollbars to keep the UI clean.
        """
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:

        if len(self.scene().items()) <= 1:
            # If there is only on item in the scene it is the placeholder text.
            # In this case we don't want to zoom out but just ignore the event
            return super().mouseDoubleClickEvent(event)

        # Get the item on the canvas that was clicked
        clicked_item = self.scene().itemAt(self.mapToScene(event.pos()), QTransform())

        if event.button() == Qt.MouseButton.LeftButton and clicked_item is None:
            # Check if the canvas is already zoomed out to fit the scene or not and zoom accordingly
            if self.freeze:
                # Reset the view center point and restore the transform from before zooming out
                self.setTransform(self.current_transform)
                self.centerOn(self.current_center)

                # Enable dragging the scene around again
                self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
                self.freeze = False
            else:
                # Store the current transform and center point to be able to zoom back in to the same position when double clicking again
                self.current_transform = self.transform()
                self.current_center = self.mapToScene(self.viewport().rect().center())

                # Disable dragging the scene around
                self.setDragMode(QGraphicsView.DragMode.NoDrag)

                # Zoom out to fit the scene
                self.fitInView(self.scene().itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)
                self.freeze = True

        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """
        Enable panning or rubber band selection based on whether the shift key is pressed
        """
        if event.button() == Qt.MouseButton.LeftButton:
            if event.modifiers() == Qt.KeyboardModifier.ShiftModifier:
                self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
            elif not self.freeze:
                self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)

        super().mousePressEvent(event)

    def viewportEvent(self, event: QEvent) -> bool:
        """
        Handle zooming for both Windows and macOS.
        For Windows, a QWheelEvent is emitted, for macOS a QNativeGestureEvent.
        """
        if isinstance(event, QWheelEvent) and sys.platform == 'win32' \
                and abs(event.angleDelta().y()) >= 50:
            # Handle zooming on Windows if the mouse wheel was scrolled "enough"
            self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
            self.zoom += 1 if event.angleDelta().y() > 0 else -1
            self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)

            # Return True to accept the event
            return True

        elif isinstance(event, QNativeGestureEvent) and sys.platform == 'darwin' \
                and event.gestureType() == Qt.NativeGestureType.ZoomNativeGesture:
            # Handle zooming on macOS if the Gesture was a ZoomGesture
            if event.gestureType() == Qt.NativeGestureType.BeginNativeGesture:
                # Set zoom value counter to 0 when a new gesture begins
                self.zoom_value_counter = 0

            # Add the "zoom amount" to the zoom value counter
            self.zoom_value_counter += event.value()

            # Check if the zoom value counter has reached the threshold to zoom a step
            if abs(self.zoom_value_counter) >= self.zoom_value_threshold:
                self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
                self.zoom += 1 if self.zoom_value_counter > 0 else -1
                self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)

                # Reset the zoom value counter
                self.zoom_value_counter = 0

            # Return True to accept the event
            return True

        return super().viewportEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        super().keyPressEvent(event)

        if event.key() == Qt.Key.Key_Plus:
            self.zoom += 1
        elif event.key() == Qt.Key.Key_Minus:
            self.zoom -= 1

    @property
    def zoom(self) -> int:
        return self._zoom

    @zoom.setter
    def zoom(self, zoom: int) -> None:
        """
        Zooms the view to the specified zoom level.
        """
        # Check if the view is frozen and return if it is because zooming is disabled when frozen
        if self.freeze:
            return

        # Check if the zoom level is within the specified range if clamping is enabled
        if self.zoom_clamp:
            if zoom < self.zoom_range[0]:
                zoom = self.zoom_range[0]
            if zoom > self.zoom_range[1]:
                zoom = self.zoom_range[1]

        # Calculate how many steps to zoom in/out
        diff = self._zoom - zoom

        # Calculate zoom factor/the amount to zoom in
        if diff > 0:
            zoom_factor = (1 / self.zoom_factor) ** diff
        elif diff < 0:
            zoom_factor = self.zoom_factor ** -diff
        else:
            zoom_factor = 1

        # Do the zooming
        self.scale(zoom_factor, zoom_factor)

        # Update the value and slider
        self._zoom = zoom

    def setZoom(self, zoom: int) -> None:
        """
        Sets the zoom level to the given value
        This function needs to be called to set the zoom level from outside this class as a slot

        :param zoom: The zoom level to set
        """
        self.zoom = zoom

