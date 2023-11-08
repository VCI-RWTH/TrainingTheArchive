from typing import List, Tuple

from PyQt6.QtWidgets import QWidget, QFormLayout, QLineEdit, QPushButton
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QCloseEvent

from SearchEngine import METASearch


class FilterWindow(QWidget):
    """
    This class represents the filter window that is used to filter the results of a search.
    The user can enter a filter for each column in the metadata table.
    The search bar grabs the current filters from this class before each search
    """

    closing = pyqtSignal()

    def __init__(self, artsearch):
        super().__init__()

        self.artsearch = artsearch
        self.filters = {}  # Store the line edits where the user enters the filters for each key in this dictionary

        self.initUI()

    def initUI(self) -> None:
        self.setWindowTitle("Filter settings")

        self.layout = QFormLayout()
        self.setLayout(self.layout)

        # Create a line edit for each key in the search engines dictionary (metadata column) and add it to the layout
        for key, search in self.artsearch.search_engines.items():
            if isinstance(search, METASearch):
                line_edit = QLineEdit()
                self.filters[key] = line_edit

                self.layout.addRow(key, line_edit)

        # Add button to clear all the filters
        self.clear_button = QPushButton('Clear filters')
        self.clear_button.clicked.connect(self.clear)

        # Add button to close the window
        self.close_button = QPushButton('Set filters')
        self.close_button.clicked.connect(self.close)

        self.layout.addWidget(self.close_button)
        self.layout.addWidget(self.clear_button)

    def clear(self) -> None:
        """
        Clears all the line edits of the filters
        """
        for line_edit in self.filters.values():
            line_edit.setText('')

    def closeEvent(self, event: QCloseEvent) -> None:
        """
        Emits the closing signal before closing the window
        This is done to notify the search bar that the window is closing and change the color of the filter button
        if there are active filters
        """
        self.closing.emit()

        super().closeEvent(event)

    def extractFilters(self) -> List[Tuple[str, str]]:
        """
        Extracts the filters from the line edits and returns them as a list of tuples (key, value)
        """
        return [(key, line_edit.text()) for key, line_edit in self.filters.items()]

    def getActive(self) -> bool:
        """
        Returns whether there are any filters

        :return: True if there are any filters, False otherwise
        """
        for line_edit in self.filters.values():
            if line_edit.text():
                return True
        return False
