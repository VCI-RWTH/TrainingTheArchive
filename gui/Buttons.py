import os

from PyQt6.QtWidgets import QPushButton, QSizePolicy
from PyQt6.QtCore import Qt, QSize, pyqtSlot
from PyQt6.QtGui import QIcon, QPaintEvent

from gui.Colors import LIGHT_BLUE


class ToggleButton(QPushButton):
    """
    A custom toggle button, that is used to toggle the personalization of the search.
    It is a circle with a star in it and a background that is either blue or white, depending on whether it is active or not.
    """
    def __init__(self):
        super().__init__()

        self.active = True  # Whether the button is active or not

        self.initUI()
        self.initPolicies()

    def initUI(self) -> None:
        # Set the qss class to ToggleButton used to style the button inside the stylesheet
        self.setProperty('qssClass', 'ToggleButton')

        # Set the icon to the star, path
        self.setIcon(QIcon(os.path.join(os.path.dirname(__file__), 'icons', 'StarsIcon.svg')))
        self.clicked.connect(self.toggle)

        self.setToolTip('Personalize Your Search by the Images\nand Groups You Have Selected on the Canvas')

    def initPolicies(self) -> None:
        # Set the size policy to fixed, so that the button does not change size
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def paintEvent(self, event: QPaintEvent) -> None:
        """
        Set the background color to blue or white, depending on whether the button is active or not
        """
        self.setStyleSheet(f"QPushButton{{background-color: {LIGHT_BLUE if self.active else 'white'};}}")

        super().paintEvent(event)

    def sizeHint(self) -> QSize:
        return QSize(40, 40)

    @pyqtSlot()
    def toggle(self) -> None:
        self.active = not self.active

    def getState(self) -> bool:
        return self.active
