from typing import List, Dict, Any

from PyQt6.QtWidgets import QScrollArea, QWidget, QHBoxLayout, QSizePolicy, QScrollBar
from PyQt6.QtCore import Qt, QSize, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QWheelEvent, QResizeEvent

from gui.ImageWidget import ImageWidgetSearchBar


class SearchResultsDisplay(QScrollArea):
    """
    This class represents the widget where the result images are shown after a search.
    It is a scroll area that lets the user scroll through the images and load new ones when the user gets near the end.
    """

    initial_amount = 15
    increase_amount = 1

    image_double_clicked = pyqtSignal(int)
    add_context_menu_triggered = pyqtSignal(int)
    put_away_context_menu_triggered = pyqtSignal(int)

    def __init__(self, artsearch):
        super().__init__()

        self.artsearch = artsearch

        self.current_images: List[int] = []  # The results of the newest search
        self.displayed_images: Dict[str, ImageWidgetSearchBar] = {}  # The images that are currently actually displayed

        # Relative position of the slider (0 is left, 1 is right) to scroll through the images
        # This is used to keep the slider in the same relative position when the range changes (e.g. when new images are added)
        self.slider_relative_value: float = 0
        self.invert_scroll: bool = False

        self.initUI()
        self.initPolicies()

    def initUI(self) -> None:
        self.setProperty('qssClass', 'SearchResultsDisplay')
        self.setWidgetResizable(True)

        # Explicitly create scrollbar in python because it cant be accessed it if it was created in C++
        self.setHorizontalScrollBar(QScrollBar(self))
        self.horizontalScrollBar().setProperty('qssClass', 'SearchResultsDisplayScrollBar')
        self.horizontalScrollBar().valueChanged.connect(self.sliderValueChange)
        self.horizontalScrollBar().rangeChanged.connect(self.sliderRangeChange)

        self.main_widget = QWidget()

        self.layout = QHBoxLayout()
        self.main_widget.setLayout(self.layout)

        self.setWidget(self.main_widget)

    def initPolicies(self) -> None:
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.MinimumExpanding)
        self.setFocusPolicy(Qt.FocusPolicy.WheelFocus)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def sizeHint(self) -> QSize:
        return QSize(0, 200)

    def wheelEvent(self, event: QWheelEvent) -> None:
        """
        Override the wheel event to scroll horizontally instead of vertically, and to load more images when the
        scrollbar is not visible and the user scrolls.
        """

        # Create a new fake event with inverted scroll direction if the user wants inverted scroll
        if self.invert_scroll:
            inverted_event = QWheelEvent(event.position(), event.globalPosition(), event.pixelDelta() * -1, event.angleDelta() * -1, event.buttons(), event.modifiers(), event.phase(), True)
            self.horizontalScrollBar().wheelEvent(inverted_event)
        else:
            self.horizontalScrollBar().wheelEvent(event)

        # Load more images if the scrollbar is not visible and the user scrolls
        if self.current_images and not self.horizontalScrollBar().isVisible():
            to_add = self.current_images[len(self.displayed_images):
                                         len(self.displayed_images) + self.increase_amount]

            for image_id in to_add:
                self.appendImage(image_id)

        super().wheelEvent(event)

    def resizeEvent(self, event: QResizeEvent) -> None:
        """
        Resize the images when the widget is resized
        """
        for image in self.main_widget.children():
            if isinstance(image, ImageWidgetSearchBar):
                image.setMaximumHeight(self.height() - self.horizontalScrollBar().height() - self.horizontalScrollBar().height())

        super().resizeEvent(event)

    @pyqtSlot(int)
    def sliderValueChange(self, value: int) -> None:
        """
        Loads more images when the slider is at 90% of its maximum value

        :param value: The current value of the slider
        """
        # Update relative value of slider to keep it in the same relative position when the range changes
        if self.horizontalScrollBar().maximum() != 0:
            self.slider_relative_value = value / self.horizontalScrollBar().maximum()
        else:
            self.slider_relative_value = 0

        # Add new images, when the user gets near the end and there are still images to add
        if value > self.horizontalScrollBar().maximum() * 0.9 and len(self.displayed_images) < len(self.current_images):
            to_add = self.current_images[len(self.displayed_images):
                                         len(self.displayed_images) + self.increase_amount]

            # Add the images
            for image_id in to_add:
                self.appendImage(image_id)
                self.horizontalScrollBar().setValue(value - 100)

    @pyqtSlot(int, int)
    def sliderRangeChange(self, min_value: int, max_value: int) -> None:
        """
        Updates the slider value when the range changes to not jump around too new images
        """
        new_value = min(self.slider_relative_value * max_value, self.horizontalScrollBar().maximum() * 0.9)

        self.horizontalScrollBar().setValue(int(new_value))

    def displayResults(self, results: List[int]) -> None:
        """
        Display the given results

        :param results: The results to display as a list of image_ids
        """
        self.current_images = results

        # Reset Display when drawing new results and reset scroll
        self.horizontalScrollBar().setValue(0)
        self.clearDisplay()

        for image_id in results[:self.initial_amount]:
            self.appendImage(image_id)

    def updateResults(self, results: List[int]) -> None:
        """
        Updates the results by only changing the images that have actually changed

        :param results: The new results to display as a list of image_ids
        """
        self.current_images = results

        # Reset scroll when drawing new results
        self.horizontalScrollBar().setValue(0)

        to_pop = []
        to_add = []

        for i in range(self.layout.count()):
            image = self.layout.itemAt(i).widget()

            try:
                # Check if the image at index i has changed
                if self.current_images[i] != image.id:
                    # Create the new image and add it to the list of images to add
                    new_image = self.createImage(self.current_images[i])

                    # These 2 lists are used to update the displayed_images dict after the loop
                    # This is done to prevent the layout from changing while iterating over it
                    to_pop.append(str(image.id))
                    to_add.append((str(self.current_images[i]), new_image))

                    # Create a callback to update the layout after the image has finished flipping out
                    # It is used to place the new image in the correct place and let it flip in
                    def callback(old_image_param=image, new_image_param=new_image):
                        index = self.layout.indexOf(old_image_param)

                        old_image_param.setParent(None)
                        self.layout.insertWidget(index, new_image_param, alignment=Qt.AlignmentFlag.AlignHCenter)

                        new_image_param.flipIn()

                    image.flipOut(callback)
            except IndexError:
                # If there are no images left to display, remove the current image
                image.flipOut()

        # Remove and add the images
        for image_id in to_pop:
            self.displayed_images.pop(image_id)
        for image_id, image in to_add:
            self.displayed_images[image_id] = image

    def clearDisplay(self) -> None:
        """
        Removes all images from the display
        """
        self.displayed_images = {}

        for i in reversed(range(self.layout.count())):
            self.layout.itemAt(i).widget().setParent(None)

    def createImage(self, image_id: int) -> ImageWidgetSearchBar:
        """
        Creates an image widget for the given image_id and connects, scales it and connects its signals

        :param image_id: The id of the image to create the widget for
        :return: The created widget
        """
        image = ImageWidgetSearchBar(image_id, self.artsearch.getImagePath(image_id), self.artsearch)

        # Set the initial pixmap and size here since the widget does not know its size yet
        height = max(100, self.height()) - self.horizontalScrollBar().height() - 5 # Catch the case where the widget is not yet displayed
        image_scaled = image.pixmap().scaled(9999, height, Qt.AspectRatioMode.KeepAspectRatio)
        image.setPixmap(image_scaled)
        image.setMaximumSize(image_scaled.size().width(), image_scaled.size().height())

        # Connect the signals
        image.double_clicked.connect(self.image_double_clicked.emit)
        image.add_triggered.connect(self.add_context_menu_triggered.emit)
        image.put_away_triggered.connect(self.putAwayTriggered)
        image.preview_left_arrow_clicked.connect(self.showPreviousPreview)
        image.preview_right_arrow_clicked.connect(self.shoNextPreview)

        return image

    @pyqtSlot(int)
    def removeImage(self, image_id: int) -> None:
        """
        Removes the image with the given image_id from the display if possible and adds a new one if possible

        :param image_id: The id of the image to remove
        """
        if str(image_id) in self.displayed_images:
            # Remove the image from the layout
            self.displayed_images[str(image_id)].setParent(None)

            # Remove the image from the dict and the list
            self.displayed_images.pop(str(image_id))
            self.current_images.remove(image_id)

            # Add a new image if possible
            if len(self.displayed_images) < len(self.current_images):
                self.appendImage(self.current_images[len(self.displayed_images)])

    def appendImage(self, image_id: int) -> None:
        """
        Appends an image to the display

        :param image_id: The id of the image to append to the display
        """
        image = self.createImage(image_id)
        self.layout.addWidget(image, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.displayed_images[str(image_id)] = image

    @pyqtSlot(int)
    def putAwayTriggered(self, image_id: int) -> None:
        """
        This slot is called when the put away action is triggered in the context menu of an image
        It removes the image and notifies the SearchBar

        :param image_id: The id of the image that should be put away
        """
        self.removeImage(image_id)
        self.put_away_context_menu_triggered.emit(image_id)

    @pyqtSlot(int)
    def showPreviousPreview(self, image_id: int) -> None:
        """
        This slot is called when the left arrow key is clicked while a preview window is open
        It displays the image that comes before the current image of the preview window in the preview window
        This has to be handled here because the order of the images is stored in this class.

        :param image_id: The id of the image that is currently displayed in the preview window
        """
        # Check if the image is still displayed
        try:
            image = self.displayed_images[str(image_id)]
        except KeyError:
            print('Image not displayed')
            return
        index = self.layout.indexOf(image)

        # Move to the previous image if possible
        if index > 0:
            image.preview_window.hide()
            self.layout.itemAt(index - 1).widget().preview_window.show()

    @pyqtSlot(int)
    def shoNextPreview(self, image_id: int) -> None:
        """
        This slot is called when the right arrow key is clicked while a preview window is open
        It displays the image that comes after the current image of the preview window in the preview window
        This has to be handled here because the order of the images is stored in this class.

        :param image_id: The id of the image that is currently displayed in the preview window
        """
        # Check if the image is still displayed
        try:
            image = self.displayed_images[str(image_id)]
        except KeyError:
            print('Image not displayed')
            return

        index = self.layout.indexOf(image)

        # Move to the next image if possible
        if index < self.layout.count() - 1:
            image.preview_window.hide()
            self.layout.itemAt(index + 1).widget().preview_window.show()

    def serialize(self) -> Dict[str, Any]:
        return {
            'current_images': self.current_images.copy(),
            'displayed_images': list(self.displayed_images.keys()).copy()
        }

    def deserialize(self, data: Dict[str, Any]) -> None:
        self.clearDisplay()

        for image_id in data['displayed_images']:
            self.appendImage(int(image_id))

        self.current_images = data['current_images']
