import os
import json
import xlsxwriter
from PIL import Image as PIL_Image

from PyQt6.QtWidgets import QMainWindow, QSplitter, QSplitterHandle, QSizePolicy, QFileDialog, QMenu, QApplication
from PyQt6.QtCore import Qt, QSize, pyqtSlot
from PyQt6.QtGui import QPaintEvent, QPainter, QAction, QIcon, QPageSize, QPageLayout, QKeyEvent, QCursor, QPen
from PyQt6.QtPrintSupport import QPrinter

from SearchEngine import METASearch

from gui.AboutWindow import AboutWindow
from gui.Canvas import Canvas
from gui.CanvasView import CanvasView
from gui.ImageWidget import ImageWidget
from gui.ImageGraphicsItem import ImageGraphicsItem
from gui.History import History
from gui.SearchBar import SearchBar
from gui.Splitter import Splitter
from gui.Tutorial import TutorialWindow
from gui.ConfigDialog import ConfigDialog

BASE_PATH = os.path.dirname(__file__)


class MainWindow(QMainWindow):
    """
    This is the main window of the entire application. In this window everything comes together.
    It also manages the menu bar and its actions (e.g. save, open, etc.)
    """
    def __init__(self, artsearch):
        super().__init__()

        self.artsearch = artsearch # This is mainly required to pass it to the other widgets (e.g. SearchBar) and to get Metadata

        # Call functions to set up the UI and the menu bar
        self.initUI()
        self.initMenuBar()

    def initUI(self) -> None:
        """
        Initializes the UI, creating the layout, the widgets that are part of the layout and the menu bar.
        """
        self.setWindowTitle("The Curator's Machine")

        # Create the widgets that are part of the layout
        self.search_bar = SearchBar(self.artsearch)
        self.canvas = Canvas()
        self.scene = self.canvas.getScene()

        self.history = History(self.search_bar, self.scene, self.artsearch)

        # Assign values to attributes that are required by the widgets
        # This could not have been done when constructing the widgets because the widgets need references to each other
        self.scene.search_bar = self.search_bar
        self.scene.artsearch = self.artsearch
        self.scene.history = self.history
        self.scene.box.artsearch = self.artsearch
        self.scene.preview_window.artsearch = self.artsearch

        self.search_bar.scene = self.scene
        self.search_bar.history = self.history

        # Add an empty timestamp to the history
        # This is done to be able to revert back to this empty timestamp after doing an undoable action
        self.history.addTimeStamp()

        # Create the (custom) splitter that contains the search bar and the canvas
        # This is done instead of just adding the two widgets to the layout, because this way the user can resize them
        self.splitter = Splitter(Qt.Orientation.Vertical)
        self.splitter.addWidget(self.search_bar)
        self.splitter.addWidget(self.canvas)

        # Create the tutorial window that is shown, when the tutorial action is called from the menubar
        self.tutorial_window = TutorialWindow(self)

        # Create the about window that is shown, when the About action is called from the menubar
        self.about_window = AboutWindow()

        # Set the central widget to the splitter, to display the splitter (containing the other widgets)
        self.setCentralWidget(self.splitter)

    def initMenuBar(self) -> None:
        """
        Creates the menu bar and adds the actions to it.
        """
        self.menu_bar = self.menuBar()

        # Add the menus to the toolbar
        file_menu = self.menu_bar.addMenu('File')
        edit_menu = self.menu_bar.addMenu('Edit')
        view_menu = self.menu_bar.addMenu('View')
        controls_menu = self.menu_bar.addMenu('Controls')
        help_menu = self.menu_bar.addMenu('Help')

        # Small function to make it easier to add an Action to a menu with fewer lines of code
        def addAction(name: str, shortcut: str, slot: pyqtSlot, menu: QMenu) -> QAction:
            action = menu.addAction(name)
            action.setShortcut(shortcut)
            action.triggered.connect(slot)
            return action

        # Add the actions and sub menus to the menus
        addAction('New Project', 'Ctrl+N', self.newFile, file_menu)
        addAction('Open Project', 'Ctrl+O', self.openFile, file_menu)
        addAction('Save Project', 'Ctrl+S', self.saveFile, file_menu)

        save_as_menu = file_menu.addMenu('Save As')
        addAction('Export as PDF', '', self.saveAsPdf, save_as_menu)
        addAction('Export in Excel', '', self.saveAsExcel, save_as_menu)

        addAction('Upload Image', '', self.uploadCustomImage, file_menu)
        addAction('Change Dataset', '', self.changeDataset, file_menu)

        addAction('Undo Last', 'Ctrl+Z', self.undo, edit_menu)
        addAction('Redo Last', 'Ctrl+Shift+Z', self.redo, edit_menu)

        addAction('Hide/Show Notes', '', self.toggleNotes, view_menu)
        addAction('Hide/Show Favorites', '', self.toggleNonFavorites, view_menu)

        # Store this action to change the icon to a checkmark when the scroll direction is inverted
        self.invert_scroll_action = addAction('Invert Scroll Direction', '', self.invertScrollDirection, controls_menu)

        language_menu = help_menu.addMenu('Set Language (search prompts)')

        # Also store these actions to change the icon to a checkmark when the language is switched
        self.english_action = addAction('English', '', self.switchToEnglish, language_menu)
        self.english_action.setIcon(QIcon(os.path.join(BASE_PATH, 'icons', 'CheckMarkIcon.svg')))

        self.german_action = addAction('German', '', self.switchToGerman, language_menu)

        addAction('Show Tutorial', '', self.tutorial, help_menu)
        addAction('About', '', self.about, help_menu)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """
        This function is called when a key is pressed.
        It is used to open the preview window when the space bar is pressed while hovering over an image.
        """
        if event.key() == Qt.Key.Key_Space:
            item = QApplication.widgetAt(QCursor.pos())

            if isinstance(item, ImageWidget):
                # For ImageWidgets (Image that are in the search bar or box) a new preview window can simply be opened
                item.preview_window.show()
            if isinstance(item.parentWidget(), CanvasView):
                # For ImageGraphicsItems (Images that are in the canvas),
                # the preview window will be updated with the new image instead of opening a new one

                # Get the GraphicsItem that is currently hovered over
                view = item.parentWidget()
                graphics_item = view.itemAt(view.mapFromGlobal(QCursor.pos()))

                if isinstance(graphics_item, ImageGraphicsItem):
                    self.scene.preview_window.setImage(graphics_item.id, graphics_item.path)
                    self.scene.preview_window.show()

        super().keyPressEvent(event)

    @pyqtSlot()
    def newFile(self) -> None:
        """
        Resets the application (except the search bar) to its initial state.
        """
        self.scene.clear()
        self.artsearch.reset()
        self.search_bar.updateResults()

        self.history.reset()
        self.history.addTimeStamp()

    @pyqtSlot()
    def openFile(self) -> None:
        """
        Opens a previously save .json file and loads the data into the application.
        """
        # Open a file dialog to select the file to open
        file = QFileDialog.getOpenFileName(self, 'Open', '', 'json-file (*.json)')

        if file and file[0]:
            # If the file is valid, load the data from the file and deserialize it
            data = json.load(open(file[0]))

            self.artsearch.deserialize(data['artsearch'])
            self.scene.deserialize(data['canvas'])

    @pyqtSlot()
    def saveFile(self) -> None:
        """
        Saves the current state of the application to a .json file.
        """
        # Open a file dialog to select the file to save to
        file = QFileDialog.getSaveFileName(self, 'Save', '', 'json-file (*.json)')

        # Serialize the current state of the application
        data = {}
        data['artsearch'] = self.artsearch.serialize()
        data['canvas'] = self.canvas.getScene().serialize()

        if file and file[0]:
            # Check if the correct file extension
            file_name = file[0]
            if file_name[-5:] != '.json':
                file_name += '.json'

            # Save the data to the file
            with open(file_name, 'w') as file:
                json.dump(data, file, indent=2)

    @pyqtSlot()
    def saveAsPdf(self) -> None:
        """
        Exports the current state of the canvas to a .pdf file.
        """
        # Open a file dialog to select the file to save to
        file = QFileDialog.getSaveFileName(self, 'Save As PDF', '', 'pdf-file (*.pdf)')

        if file and file[0]:
            file_name = file[0]
            if file_name[-4:] != '.pdf':
                file_name += '.pdf'

            # Create a printer and configure it to output a A3 landscape pdf
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(file_name)
            printer.setPageSize(QPageSize(QPageSize.PageSizeId.A3))
            printer.setPageOrientation(QPageLayout.Orientation.Landscape)

            # Create painter to render the canvas
            painter = QPainter(printer)
            painter.begin(printer)

            # Render the canvas
            self.scene.render(painter, source=self.scene.itemsBoundingRect())
            painter.end()

    @pyqtSlot()
    def saveAsExcel(self) -> None:
        """
        Saves the images and groups that are currently on the canvas to an Excel file using xlsxwriter.
        Including the Metadata of the images if available.
        """
        file = QFileDialog.getSaveFileName(self, 'Save As Excel', '', 'xlsx-file (*.xlsx)')

        if file and file[0]:
            file_name = file[0]
            if file_name[-5:] != '.xlsx':
                file_name += '.xlsx'

            # Create a new Excel workbook and worksheet to write to
            workbook = xlsxwriter.Workbook(file_name)
            worksheet = workbook.add_worksheet()

            # Format the cells, so that the text is centered
            cell_format = workbook.add_format()
            cell_format.set_align('center')
            cell_format.set_align('vcenter')

            # In this dictionary there is one entry for each image, in which the groups the image is in are stored
            # Initialize the dictionary with empty lists for each image
            groups_dict = {image.id: [] for image in self.scene.getImages()}

            # Add the groups to the dictionary
            for group in self.scene.getGroups():
                for image in group.getImages():
                    groups_dict[image.id].append(group.getName())

            # In this variable the index of the last column is stored
            # Start at 1, because the first column is reserved for the image
            last_column = 1

            # Write the header for each column using the METASearch engine types in the artsearch object
            for search_engine in self.artsearch.search_engines.values():
                if isinstance(search_engine, METASearch):
                    # Write the name of each METASearch engine in the first row (Header row)
                    worksheet.write(0, last_column, search_engine.type, cell_format)

                    last_column += 1

            # Write the header for the groups column in the last column
            worksheet.write(0, last_column, 'Groups')
            # Set the width of the columns
            worksheet.set_column(0, last_column, 10)

            # In this loop the Metadata for each image is written to the worksheet
            for row, image in enumerate(self.scene.getImages()):
                current_row = row + 1  # Skip the header

                # Sets the height of the row to 100 to fit the small image
                worksheet.set_row(current_row, 100)

                # Write the METAdata for the current image into the corresponding columns
                for col, search_engine in enumerate(self.artsearch.search_engines.values()):
                    if search_engine.type != 'CLIP':
                        # Get the Metadata value for the current image
                        value = search_engine.search_by_id(image.id)

                        # Only write the value if it is an actual value and not 'nan'
                        if value and value != 'nan':
                            worksheet.write(current_row, col, value, cell_format)

                # Write the groups the image is in into the last column (Groups column)
                worksheet.write(current_row, last_column, ', '.join(groups_dict[image.id]), cell_format)

                # Add preview Image
                # Since the images can have different DPIs, the image has to be scaled accordingly
                original_image = PIL_Image.open(self.artsearch.paths[image.id])
                original_dpi = original_image.info['dpi']

                # Determine the original width of the image and the width after scaling it (with respect to its dpi)
                original_width = original_image.size[0]
                scaled_width = self.artsearch.image_widths[image.id] * (original_dpi[0] / 72)  # Adjustment depending on the dpi necessary

                scale_factor = scaled_width / original_width

                # Insert the image into the first column
                worksheet.insert_image(current_row,
                                       0,
                                       self.artsearch.paths[image.id],
                                       {'x_scale': scale_factor, 'y_scale': scale_factor, 'object_position': 2})

            # Close the workbook to save it
            try:
                workbook.close()
            except xlsxwriter.exceptions.FileCreateError:
                print("File currently open")

    @pyqtSlot()
    def changeDataset(self) -> None:
        config_dialog = ConfigDialog()
        config_dialog.exec()
        
    @pyqtSlot()
    def uploadCustomImage(self) -> None:
        """
        Asks the user to select an image and adds it to the canvas.
        """
        file = QFileDialog.getOpenFileName(self, 'Upload Custom Image', '', 'image-file (*.jpg *.jpeg *.png *.tga *.bmp)')

        if file and file[0]:
            self.scene.addCustomImage(file[0])

    @pyqtSlot()
    def undo(self) -> None:
        """
        Undoes the last action by forwarding the action to the history
        """
        self.history.undo()

    @pyqtSlot()
    def redo(self) -> None:
        """
        Redoes the last action by forwarding the action to the history
        """
        self.history.redo()

    @pyqtSlot()
    def toggleNotes(self) -> None:
        """
        Toggles the opacity of all notes by forwarding the action to the scene where the notes are stored
        """
        self.scene.toggleNotes()

    @pyqtSlot()
    def toggleNonFavorites(self) -> None:
        """
        Toggles the opacity of all images that not-favorite by forwarding the action to the scene where the images are stored
        """
        self.scene.toggleNonFavorites()

    @pyqtSlot()
    def invertScrollDirection(self) -> None:
        """
        Inverts the scroll direction for scrolling through the results in the ResultsDisplay (Component of the SearchBar)
        and adds a checkmark to the menu item if the scroll direction is inverted
        """
        self.search_bar.results_display.invert_scroll = not self.search_bar.results_display.invert_scroll

        if self.search_bar.results_display.invert_scroll:
            self.invert_scroll_action.setIcon(QIcon(os.path.join(BASE_PATH, 'icons', 'CheckMarkIcon.svg')))
        else:
            self.invert_scroll_action.setIcon(QIcon(''))


    @pyqtSlot()
    def switchToEnglish(self) -> None:
        """
        Switches the language of the search to English and adjusts the checkmark icon for the language menu items
        """
        # Disable the English menu item and enable the German menu item because the language is now English
        self.english_action.setEnabled(False)
        self.german_action.setEnabled(True)

        # Adjust the checkmark icons
        self.english_action.setIcon(QIcon(os.path.join(BASE_PATH, 'icons', 'CheckMarkIcon.svg')))
        self.german_action.setIcon(QIcon(''))

        # Change the search language to English
        self.artsearch.lang = 'EN'

    @pyqtSlot()
    def switchToGerman(self) -> None:
        """
        Switches the language of the search to German and adjusts the checkmark icon for the language menu items
        """
        # Disable the German menu item and enable the English menu item because the language is now German
        self.english_action.setEnabled(True)
        self.german_action.setEnabled(False)

        # Adjust the checkmark icons
        self.english_action.setIcon(QIcon(''))
        self.german_action.setIcon(QIcon(os.path.join(BASE_PATH, 'icons', 'CheckMarkIcon.svg')))

        # Change the search language to German
        self.artsearch.lang = 'DE'

    @pyqtSlot()
    def tutorial(self) -> None:
        """
        Opens the tutorial window
        """
        self.tutorial_window.show()

    @pyqtSlot()
    def about(self) -> None:
        """
        Opens the about window
        """
        self.about_window.show()
