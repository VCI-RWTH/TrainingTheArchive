from typing import List, Dict

from PyQt6.QtWidgets import QWidget, QPushButton, QLabel, QHBoxLayout, QVBoxLayout, QGraphicsBlurEffect, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QCloseEvent, QFont, QShowEvent

PAGE_1_TEXT = """Welcome to <i>The Curator’s Machine</i>.<br><br>
This is a prototype to help explore museum collections more easily and to create new ideas for exhibition projects.<br><br>
With the help of AI, you can search for anything you like and see what the machine finds. If an artwork fits well, it can be worked on further. If it is not right, it can be sorted into the box.<br><br>
Through the personalized use of the tool, the AI model adjusts to you and the search results become more precise. You will discover the collection in a very personal way. Let’s start!"""

PAGE_2_TEXT = """Your search begins. Type in a term or even a word phrase and describe what you want to find. You can use technical terms or stylistic features such as 'painting with red color or drawing with fruits in the style of Monet.' <br><br>
Note that the search algorithm has learned from the Internet and shows you what is commonly known there.<br><br>
You can scroll the search results all the way to the right. The images will continuously re-sort along your selection, but more on that in a moment.<br><br>
Pressing the space bar shows the preview of an image and the right mouse button opens the context menu.<br><br>
The clock icon provides you with your search history and by clicking on the image search icon you can upload an image and find visually similar images in your collection.<br><br>
You can also search for any other image by dragging and dropping it into the search bar.<br><br>
You can enlarge or reduce the size of the search results window by grabbing the dotted handle and expanding or collapsing it."""

PAGE_3_TEXT = """Now let’s get to work. If you want to add an image to your selection on the canvas, you can double-click on it, select the command from the context menu, or drag and drop it.<br><br>
An image placed on the canvas shows the AI that you find it interesting, and the learning model re-orders search suggestions along your positive selections—have you noticed that the images flip and rearrange themselves in real time?<br><br>
If you ever want to turn this assistant off, just click the blue <i>wizard</i> button and you’ll see the general search results without special personalization.<br><br>
Sometimes it is helpful to switch back and forth between these two modes.<br><br>
If you find a search result does not fit your search, you can put it away using the respective command in the context menu. The AI ranks non-optimal matching images and sorting them further to the right in the search results."""

PAGE_4_TEXT = """Let’s organize our exhibition on the canvas. You can zoom the workspace in and out by using a pinching gesture on the trackpad or by turning the mouse wheel.<br><br>
If you ever lose track, just double-click (again to jump back) on a white area in the canvas and you’ll get an overview of all the images and organizational elements you’ve chosen.<br><br>
The latter can be <i>sticky notes</i> or <i>favorites</i>, which you can activate in the toolbar or find in the context menu by right-clicking on an image.<br><br>
Of course, <i>undo</i> and <i>redo</i> of your last steps should not be missing in case you have made a mistake.<br><br>
If an image is wrongly placed on the canvas, you can simply drag it back to the search results panel or <i>put</i> it <i>back</i> using the specific command.<br><br>
If you don’t like the image at all, the <i>remove</i> command puts the image into the box (more on this in a moment). Just try it out!"""

PAGE_5_TEXT = """We’re now getting into curating. If you combine images thematically, you can also group them accordingly.<br><br>
Simply select <i>add a group</i> in the toolbar. You can now drag images into your group, enlarge them by dragging the corners of the frame and name them in a way that makes sense to you.<br><br>
If you have already selected several images on the canvas (hold <i>shift</i> and click on the images or directly drag a frame on the canvas with shift), the group will be placed around your selection.<br><br>
Pretty neat, isn’t it? Note that the clusters and the titles of the groups show the AI how you want to contextualize the art and that’s what affects the sorting of the search results as well.<br><br>
"""

PAGE_6_TEXT = """Are you looking for something specific? Then the filter options via the icon in the search bar will help you to narrow down your search results. The filters can be activated by placing the desired filter terms in the respective column ('and'-operation).<br><br>
It is important that the filter keywords correspond to the exact spelling of the linked metadata, e.g. from the MuseumPlus export, so that these entries can be found and used.<br><br>
Of course, filter options are only possible if you have provided the corresponding meta information while installing your dataset (more about this in a moment).
"""

PAGE_7_TEXT = """Remember the box on the right side of the window?<br><br>
This is where the images end up that you don’t find fitting and have ruled out of the search results for your current session.<br><br>
Click on the box to open it or slide it open using the dotted handle. You can also find deleted notes here.<br><br>
If you like an image, which you can also preview, from the box again, you can drag and drop it or use the right-click context menu to put it back on the canvas.<br><br>
Note that the AI will immediately indicate that you became interested in the image and will positively reinforce search results similar to the returned image.<br><br>
Of course, you can move the image back to the search results from the canvas or use the dedicated context menu. In that case, the image feeds neutrally into the sorting of the search results. Test a bit to see the effect."""

PAGE_8_TEXT = """We are almost done here. Let’s take a look at the main menu.<br><br>
In <i>file</i> you can save your project, start a new one or open a previous session. You can also save your result as a PDF or excel list. Furthermore, you can upload images from your hard drive directly to the canvas and work with them (e.g., search for similar images in the collection).<br><br>
You can also change your dataset via this menu, but more about that in a moment.<br><br>
In <i>view</i> you can hide and show your <i>favorites</i> and <i>sticky notes</i> that should help you to tidy up your canvas.<br><br>
In <i>controls</i> you can change the direction of scrolling through the search results, according to your preferences.<br><br>
Finally, via <i>help</i> you change the language of the search prompt input. Note that the German language input is linked to a dictionary that translates back to English, which may not always work perfectly. Therefore, <i>The Curator’s Machine</i> works best in English."""

PAGE_9_TEXT = """You are almost ready to start using <i>The Curator’s Machine</i>.<br><br>
Once you have familiarized yourself with the software using our open-source test dataset, you can begin to connect your own collection to the tool.<br><br>
Go to the main menu <i>file</i> and to <i>change dataset</i>.<br><br>
Setting up your collection can be done either by creating a <i>new link</i> or by relinking <i>existing data</i>.<br><br>
If you are starting fresh, specify the path to the folder where your images are stored on your hard drive. Also set the path to your metadata file related to the images.<br><br>
Initially, your metadata CSV is required to contain a column of values that belong to the related image data and uniquely identify it (e.g., via an object ID that also corresponds to the file name of the respective image).<br><br>
Note that you don’t have to link meta information if you can’t provide any.<br><br>
Don’t forget to name your collection. Setting up the link to your collection may take some time—don’t get impatient.<br><br>
If you have already successfully linked a collection dataset, you can select it (again) by specifying the paths to the existing files.<br><br>
You've done it, have fun curating with <i>The Curator’s Machine</i>."""


class TutorialPages:
    """
    A class that stores the pages/steps of the tutorial.
    A single pace is a dict with a title, description, and list of widgets that should be blurred,
    when displaying the page
    """
    def __init__(self, main_window):
        self.main_window = main_window # Store the main window to be able to blur the widgets

        self.pages: List[Dict] = [] # List of pages
        self.current_page = 0 # The index of the current page

        # Create the tutorial pages
        self.initPages()

    def getCurrentPage(self) -> Dict:
        """
        Returns the current page as a dict

        :return: The current page as a dict with keys 'title', 'description', and 'widgets'
        """
        return self.pages[self.current_page]

    def nextPage(self) -> Dict:
        """
        Increments the current page by 1 and returns the new page

        :return: The new page
        """
        if self.current_page + 1 < len(self.pages):
            self.current_page += 1
        return self.getCurrentPage()

    def previousPage(self) -> Dict:
        """
        Decrements the current page by 1 and returns the new page
        """
        if self.current_page > 0:
            self.current_page -= 1
        return self.getCurrentPage()

    def setPage(self, page: int) -> None:
        """
        Sets the current page to the given page number

        :param page: The index of the page to set the current page to
        """
        if 0 <= page < len(self.pages):
            self.current_page = page

    def initPages(self) -> None:
        """
        Initializes the tutorial pages by adding them to the list of pages
        """
        # Handy variables to make the code more readable
        main_window = self.main_window
        search_bar = main_window.search_bar
        results_display = search_bar.results_display
        canvas = main_window.canvas

        # Add pages
        self.addPage('Welcome', PAGE_1_TEXT, [main_window])
        self.addPage('Searching', PAGE_2_TEXT, [canvas])
        self.addPage('The Canvas', PAGE_3_TEXT, [])
        self.addPage('Navigation', PAGE_4_TEXT, [search_bar])
        self.addPage('Groups', PAGE_5_TEXT, [search_bar])
        self.addPage('Filter Options', PAGE_6_TEXT, [canvas])
        self.addPage('The Box', PAGE_7_TEXT, [search_bar])
        self.addPage('Projects', PAGE_8_TEXT, [main_window])
        self.addPage('Using your Images', PAGE_9_TEXT, [main_window])


    def addPageDict(self, page_dict: Dict) -> None:
        """
        Adds a page to the list of pages by giving a dict with the keys "title", "description", and "blurred_widgets"

        :param page_dict: The dict containing the page information
        """
        self.pages.append(page_dict)

    def addPage(self, title: str, content: str, blurred_widgets: List[QWidget] = None) -> None:
        """
        Adds a page to the list of pages by giving the title, content, and list of widgets to blur.
        Can be used to add a page, without creating a dict first

        :param title: The title of the page
        :param content: The content of the page
        :param blurred_widgets: The list of widgets to blur
        """
        page_dict = {
            'title': title,
            'content': content,
            'blurred_widgets': blurred_widgets
        }
        self.pages.append(page_dict)


class TutorialWindow(QWidget):
    """
    The widget that displays the individual tutorial pages/steps in a separate window.
    It is also able to blur the widgets to focus on the current step.
    """
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window # The main window, needed to blur the widgets
        self.tutorial_pages = TutorialPages(self.main_window) # The tutorial pages object, needed to get the pages

        # Set up the UI
        self.initUI()
        self.initPolicies()

    def initUI(self) -> None:
        """
        Initializes the UI of the tutorial window
        It consists of 2 labels to display the title and content of the page,
        and 2 buttons to go to the next and previous pages
        """
        self.setWindowTitle('Tutorial')
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)

        # Label to display the title of the page
        self.title = QLabel(self)
        self.title.setFont(QFont('Arial', 20))
        self.title.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        # Label to display the content of the page
        self.content = QLabel(self)
        self.setFont(QFont('Arial', 15))
        self.content.setWordWrap(True)
        self.content.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.content_layout = QVBoxLayout()
        self.content_layout.addWidget(self.title)
        self.content_layout.addWidget(self.content)

        self.layout = QHBoxLayout(self)

        # Create the buttons to go to the next and previous pages
        self.previous_button = QPushButton('<')
        self.previous_button.clicked.connect(self.previousPage)
        self.previous_button.setMinimumSize(25, 50)

        self.next_button = QPushButton('>')
        self.next_button.clicked.connect(self.nextPage)
        self.next_button.setMinimumSize(25, 50)

        self.layout.addWidget(self.previous_button)
        self.layout.addLayout(self.content_layout)
        self.layout.addWidget(self.next_button)

    def initPolicies(self) -> None:
        """
        Initializes the policies of the tutorial window
        """
        self.setMinimumSize(600, 500)

    def loadPage(self, page: Dict) -> None:
        """
        Loads the content of a given page into the tutorial window

        :param page: The page as a dict with keys 'title', 'content', and 'blurred_widgets'
        """
        # Set the title and content of the page
        self.title.setText(page['title'])
        self.content.setText(page['content'])

        # Create the blur effect
        blur = QGraphicsBlurEffect()
        blur.setBlurRadius(10)

        # Unblur all the widgets and blur only the widgets that need to be blurred
        self.unblurWidgets()
        if page['blurred_widgets']:
            for widget in page['blurred_widgets']:
                widget.setGraphicsEffect(blur)

        self.main_window.update()

    @pyqtSlot()
    def nextPage(self) -> None:
        page = self.tutorial_pages.nextPage()
        self.loadPage(page)

    @pyqtSlot()
    def previousPage(self) -> None:
        page = self.tutorial_pages.previousPage()
        self.loadPage(page)

    def unblurWidgets(self) -> None:
        """
        "Unblurs" all the widgets that were blurred by the tutorial window
        """
        for page in self.tutorial_pages.pages:
            if page['blurred_widgets']:
                for widget in page['blurred_widgets']:
                    widget.setGraphicsEffect(None)

    def showEvent(self, event: QShowEvent) -> None:
        """
        Overrides the show event to load the first page when shown
        """
        self.tutorial_pages.setPage(0)
        self.loadPage(self.tutorial_pages.getCurrentPage())

        return super().showEvent(event)

    def closeEvent(self, event: QCloseEvent) -> None:
        """
        Overrides the close event to "unblur" the widgets before closing the window
        """
        self.unblurWidgets()

        return super().closeEvent(event)
