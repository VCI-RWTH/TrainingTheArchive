import os
from typing import Dict, Any

from PyQt6.QtWidgets import QMainWindow, QGraphicsScene, QSplitter, QSizePolicy, QWidget, QSlider, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt, pyqtSlot, QSize, QPropertyAnimation, QEasingCurve, QRect
from PyQt6.QtGui import QAction, QIcon

from gui.Box import BoxButton
from gui.CanvasView import CanvasView
from gui.Splitter import Splitter

BASE_PATH = os.path.dirname(__file__)


class Canvas(QMainWindow):
    """
    A container for the CanvasView class to add the toolbar using the MainWindow toolbar functionality.
    So this class is only responsible to manage the toolbar and its actions.
    and it mainly calls the functions of the actual scene when the user clicks on a button in the toolbar.
    """
    def __init__(self):
        super().__init__()

        # Create the splitter between the canvas and the box to let the user resize them
        self.splitter = Splitter(Qt.Orientation.Horizontal)
        self.splitter.splitterMoved.connect(self.splitterMoved)

        # Create the actual canvas view, where the canvas will be displayed
        self.canvas_view = CanvasView()

        # Create the box, where the images that are removed from the canvas will go
        # and act as negative examples for the search
        self.box = self.canvas_view.scene().box

        self.splitter.addWidget(self.canvas_view)
        self.splitter.addWidget(self.box)
        self.splitter.setSizes([1, 0])

        # Prevent the canvas from being collapsed
        self.splitter.setCollapsible(0, False)
        self.splitter.setCollapsible(1, True)

        self.setCentralWidget(self.splitter)

        # Call the function to set up the toolbar
        self.initToolbar()

    def initToolbar(self) -> None:
        """
        Create the toolbar and add the actions, zoom controls and box_button to it.
        """
        main_toolbar = self.addToolBar('Tools')
        main_toolbar.setProperty('qssClass', 'CanvasToolBar')

        # Small function to make it easier to add an Action to the toolbar with fewer lines of code
        def addAction(icon_path: str, name: str, slot: pyqtSlot) -> None:
            action = QAction(QIcon(icon_path), name, self)
            action.setProperty('qssClass', 'CanvasToolBar')
            action.triggered.connect(slot)
            main_toolbar.addAction(action)

        # Add the actions to the toolbar
        addAction(os.path.join(BASE_PATH, 'icons', 'GroupIcon.svg'), 'Add a Group', self.createGroup)
        addAction(os.path.join(BASE_PATH, 'icons', 'NoteIcon.svg'), 'Stick a Note', self.createNote)
        addAction(os.path.join(BASE_PATH, 'icons', 'StarIcon.svg'), 'Favorite', self.favorite)
        addAction(os.path.join(BASE_PATH, 'icons', 'UndoIcon.svg'), 'Undo Last', self.undo)
        addAction(os.path.join(BASE_PATH, 'icons', 'RedoIcon.svg'), 'Redo Last', self.redo)
        addAction(os.path.join(BASE_PATH, 'icons', 'HelpIcon.svg'), 'Open Tutorial', self.openTutorial)

        # Add a spacer (empty widget) to the toolbar to make the box_button stay on the right side
        spacer = QWidget()
        spacer.setProperty('qssClass', 'CanvasToolBarSpacer')
        spacer.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed)
        spacer.setMaximumHeight(1)
        main_toolbar.addWidget(spacer)

        # Create the button to open/close the box
        self.box_button = BoxButton()
        self.box_button.setProperty('qssClass', 'CanvasToolBar')
        self.box_button.clicked.connect(self.boxClicked)

        main_toolbar.addWidget(self.box_button)

    def splitterMoved(self, pos: int, index: int) -> None:
        """
        Update the maximum width of the box to ensure that it will not exceed half of the canvas width,
        even after the user resized the window.
        Also trigger the correct animation for the box_button based on the boxs state.

        :param pos: The position of the splitter handle
        :param index: The index of the splitter handle that was moved
        """
        self.box.setMaximumWidth(self.width() // 2)

        if self.box_button.open and pos == self.splitter.getRange(1)[1]:
            self.box_button.close_animation.start()
            self.box_button.open = False
        elif not self.box_button.open and pos != self.splitter.getRange(1)[1]:
            self.box_button.open_animation.start()
            self.box_button.open = True

    @pyqtSlot()
    def createGroup(self) -> None:
        self.canvas_view.scene().addGroup()

    @pyqtSlot()
    def createNote(self) -> None:
        self.canvas_view.scene().addNote()

    @pyqtSlot()
    def favorite(self) -> None:
        self.canvas_view.scene().favorite()

    @pyqtSlot()
    def undo(self) -> None:
        self.canvas_view.scene().history.undo()

    @pyqtSlot()
    def redo(self) -> None:
        self.canvas_view.scene().history.redo()

    @pyqtSlot()
    def openTutorial(self) -> None:
        self.parent().parent().tutorial()

    @pyqtSlot()
    def boxClicked(self) -> None:
        """
        Trigger the correct animation for the box_button based on the boxs state
        """
        splitter_max = self.splitter.getRange(1)[1]
        splitter_pos = self.splitter.handle(1).x()

        # Either open or close the box based on its current state
        if splitter_pos == splitter_max:
            # Box currently closed -> Open it
            self.box_button.open_animation.start()
            self.openBox()
            self.box.setMaximumWidth(self.width() // 2)
        else:
            # Box currently open -> Close it
            self.box_button.close_animation.start()
            self.closeBox()

    def openBox(self):
        """
        Opens the box with an animation to take 1/4 of the canvas width
        """
        # Calculate starting and ending position for the animation
        # start = 0
        # end = 3/4 of the canvas width
        handle = self.splitter.handle(1)
        max = self.splitter.getRange(1)[1]

        start_x = max
        end_x = (3 * max) // 4

        start = QRect(start_x, handle.y(), handle.width(), handle.height())
        end = QRect(end_x, handle.y(), handle.width(), handle.height())

        # Create and trigger the animation
        self.open_animation = QPropertyAnimation(self.splitter.handle(1), b'geometry')
        self.open_animation.setStartValue(start)
        self.open_animation.setEndValue(end)
        self.open_animation.setDuration(400)
        self.open_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.open_animation.valueChanged.connect(self.animationValueChanged)
        self.open_animation.start()

    def closeBox(self):
        """
        Closes the box with an animation
        """
        # Calculate starting and ending position for the animation
        # start = current position
        # end = 0
        handle = self.splitter.handle(1)

        start_x = handle.x()
        end_x = self.splitter.getRange(1)[1]

        start = QRect(start_x, handle.y(), handle.width(), handle.height())
        end = QRect(end_x, handle.y(), handle.width(), handle.height())

        # Create and trigger the animation
        self.close_animation = QPropertyAnimation(self.splitter.handle(1), b'geometry')
        self.close_animation.setStartValue(start)
        self.close_animation.setEndValue(end)
        self.close_animation.setDuration(400)
        self.close_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.close_animation.valueChanged.connect(self.animationValueChanged)
        self.close_animation.start()

    def animationValueChanged(self, value: QRect):
        """
        Update the splitter while the animation is running, to actually display the animation

        :param value: The geometry of the handle (x, y, width, height)
        """
        max = self.splitter.getRange(1)[1]

        self.splitter.setSizes([value.x(), max - value.x()])

    def getScene(self) -> QGraphicsScene:
        return self.canvas_view.scene()

    def serialize(self) -> Dict[str, Any]:
        return self.canvas_view.serialize()
