import sys
from typing import Dict, Any

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import Qt, pyqtSlot, QTimer

from SearchEngine import SearchEngine

from gui.Buttons import ToggleButton
from gui.Filters import FilterWindow
from gui.ImageGraphicsItem import ImageGraphicsItem
from gui.ImageWidget import ImageWidget
from gui.SearchInput import SearchInput
from gui.SearchResultsDisplay import SearchResultsDisplay

NO_SEARCH = -1
TEXT_SEARCH = 0
IMAGE_SEARCH = 1


class SearchBar(QWidget):
    """
    This class represents the search bar at the top of the main window.
    It is used to get the search inputs from the user and display the results.
    It however NOT responsible for actually performing the search. This is done in the ArtSearch class.
    The SearchBar mainly consists of the SearchInput and the SearchResultsDisplay.
    """
    def __init__(self, artsearch):
        super().__init__()

        # scene and history are set by the main window after the canvas is created
        self.artsearch = artsearch
        self.scene = None
        self.history = None

        self.filters = FilterWindow(self.artsearch)
        self.filters.closing.connect(self.filtersClosing)

        # Store the last search so that it can be repeated when updating the results
        self.last_search = None
        self.last_search_type = NO_SEARCH

        self.search_lock = False  # Lock to prevent searching too quickly

        # Set up the UI and policies
        self.initUI()
        self.initPolicies()

    def initUI(self) -> None:
        """
        Initializes the UI by setting up the layout, creating the widgets and adding slot functions
        """
        # Create the main layout of the search bar
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # The bar_layout is the layout for the search input and the toggle button
        self.bar_layout = QHBoxLayout()

        self.search_input = SearchInput()
        self.search_input.text_search_clicked.connect(self.textSearch)
        self.search_input.image_search_clicked.connect(self.imageSearch)
        self.search_input.filter_clicked.connect(self.filters.show)
        self.search_input.image_dropped.connect(lambda image_id: self.imageSearch(self.artsearch.getImagePath(image_id)))

        self.toggle_button = ToggleButton()
        self.toggle_button.clicked.connect(self.toggleClicked)

        # The results display is the widget that displays the results of the search
        self.results_display = SearchResultsDisplay(self.artsearch)
        self.results_display.image_double_clicked.connect(lambda image_id: self.scene.addImage(image_id))
        self.results_display.add_context_menu_triggered.connect(lambda image_id: self.scene.addImage(image_id))
        self.results_display.put_away_context_menu_triggered.connect(self.putAwayContextMenuTriggered)
        self.results_display.hide()

        # Add the search input and toggle button and align it in the horizontal center
        self.bar_layout.addStretch()
        self.bar_layout.addWidget(self.search_input)
        self.bar_layout.addWidget(self.toggle_button)
        self.bar_layout.addStretch()

        self.layout.addLayout(self.bar_layout)
        self.layout.addWidget(self.results_display)

    def initPolicies(self) -> None:
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

    @pyqtSlot(str)
    def textSearch(self, text: str) -> None:
        """
        Performs a text search with the given text and displays the results in the results display

        :param text: The search prompt
        """
        if self.search_lock:
            # If the search lock is active, the search is not performed
            return

        # Set the search lock to prevent searching too quickly
        self.search_lock = True
        QTimer.singleShot(1000, lambda: setattr(self, 'search_lock', False))

        # Update the last_search variables to update the results correctly when something changes on the canvas
        self.last_search = text
        self.last_search_type = TEXT_SEARCH

        # Set the display type of the search input to text (can be 'image' of an image is used for the search)
        self.search_input.input_field.line_edit.setDisplayType('text')
        self.search_input.input_field.clearFocus()

        # Display the search results
        results = self.artsearch.text_search(text, self.filters.extractFilters())
        self.results_display.show()
        self.results_display.displayResults(results)
        self.history.addTimeStamp()

    @pyqtSlot(str)
    def imageSearch(self, image_path: str) -> None:
        """
        Performs an image search with the given image and displays the results in the results display

        :param image_path: The path to the image that is used for the search
        """
        if self.search_lock:
            # If the search lock is active, the search is not performed
            return

        # Set the search lock to prevent searching too quickly
        self.search_lock = True
        QTimer.singleShot(1000, lambda: setattr(self, 'search_lock', False))

        # Update the last_search variables to update the results correctly when something changes on the canvas
        self.last_search = image_path
        self.last_search_type = IMAGE_SEARCH

        # Replace forward slashes with backslashes on windows
        if sys.platform == 'win32':
            image_path = image_path.replace('/', '\\')

        # Add "custom" images to scene
        if image_path.encode() not in self.artsearch.paths:
            self.scene.addCustomImage(image_path)

        # Display the image in the search input as a small "preview"
        self.search_input.input_field.line_edit.setDisplayType('image')
        self.search_input.input_field.line_edit.setText('<image search>')
        self.search_input.input_field.line_edit.setImage(image_path)
        self.search_input.input_field.addCurrentItem()
        self.search_input.input_field.line_edit.setText(' ')

        # Display the search results
        results = self.artsearch.image_search(image_path, self.filters.extractFilters())
        self.results_display.show()
        self.results_display.displayResults(results)
        self.history.addTimeStamp()

    def updateResults(self) -> None:
        """
        Updates the search results by repeating the last performed search.
        This is called whenever something changes on the canvas (e.g. a new image is added)
        """
        # Check if a search was performed before and if the "use embedding" toggle button is checked.
        # If it is not updating the results will not do anything and therefore is not done
        if self.last_search_type != NO_SEARCH and self.toggle_button.getState():
            if self.last_search_type == TEXT_SEARCH:
                results = self.artsearch.text_search(self.last_search, self.filters.extractFilters())
            else:
                results = self.artsearch.image_search(self.last_search, self.filters.extractFilters())

            self.results_display.updateResults(results)

    @pyqtSlot()
    def toggleClicked(self) -> None:
        """
        Slot function that is called whenever the "use embedding" toggle button is clicked.
        It disables/enables all the search engines of the artsearch object and updates the results
        """
        for key, search in self.artsearch.search_engines.items():
            if isinstance(search, SearchEngine):
                search.use_embedding = self.toggle_button.getState()

        # Update results even if the toggle button is not checked
        # This is basically the same as calling updateResults() but since update results checks if the toggle button
        # is checked it would not do anything in that case
        if self.last_search_type != NO_SEARCH:
            if self.last_search_type == TEXT_SEARCH:
                results = self.artsearch.text_search(self.last_search, self.filters.extractFilters())
            else:
                results = self.artsearch.image_search(self.last_search, self.filters.extractFilters())

            self.results_display.updateResults(results)

    @pyqtSlot()
    def filtersClosing(self) -> None:
        """
        Slot function that is called whenever the filters widget is closed.
        It updates the search results
        """
        self.search_input.setFilterIcon(self.filters.getActive())
        self.updateResults()

    def putAwayContextMenuTriggered(self, image_id: int) -> None:
        """
        Slot function that is called whenever the "Put away" context menu action of an image is triggered.
        It removes the image from the search bar and adds it to the box and adjusts the weight accordingly

        :param image_id: The id of the image that was clicked
        """
        self.scene.box.addImage(image_id)
        self.artsearch.setImageNegative(image_id)
        self.updateResults()
        self.history.addTimeStamp()


    def getLastSearchTerm(self) -> str:
        """
        Function to access the last search term, to be used as group name
        """
        if self.last_search_type == TEXT_SEARCH:
            return self.last_search
        else:
            return ''

    def removeImage(self, image_id: int) -> None:
        """
        Removes an image from the results display

        :param image_id: The id of the image to remove
        """
        self.results_display.removeImage(image_id)

    def serialize(self) -> Dict[str, Any]:
        return {
            'last_search_type': self.last_search_type,
            'last_search': self.last_search,
            'search_input': self.search_input.serialize(),
            'results_display': self.results_display.serialize()
        }

    def deserialize(self, data: Dict[str, Any]) -> None:
        self.last_search_type = data['last_search_type']
        self.last_search = data['last_search']

        self.search_input.deserialize(data['search_input'])
        self.results_display.deserialize(data['results_display'])