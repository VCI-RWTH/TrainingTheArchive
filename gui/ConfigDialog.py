import os
import shutil
import json
from typing import Tuple

from PyQt6.QtWidgets import QStackedWidget, QWidget, QVBoxLayout, QFormLayout, QPushButton, QLabel, QDialog, QLineEdit, QFileDialog, QProgressDialog, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot, QThread
from PyQt6.QtGui import QIcon

from scripts.generate_dataset import generate_dataset

from gui.Util import showError, copyFile, default_preprocessing

ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Constants to make the code more readable
INITIAL_WIDGET = 0
GENERATE_WIDGET = 1
EXISTING_CONFIG_WIDGET = 2
EXISTING_DATA_WIDGET = 3


class ConfigDialog(QDialog):
    """
    This is the widget in which the user can change their config and therefore the images that are used for the app

    It contains a stacked widget that contains all the widgets that are used in the dialog, for all the different actions.
    """
    def __init__(self):
        super().__init__()

        self.initUI()

    def initUI(self) -> None:
        self.setWindowTitle('Setup collection')

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.stacked_widget = QStackedWidget()
        self.layout.addWidget(self.stacked_widget)

        initial_widget = InitialWidget()
        initial_widget.change_widget.connect(self.changeWidget)
        self.stacked_widget.addWidget(initial_widget)

        generate_widget = GenerateWidget()
        generate_widget.change_widget.connect(self.changeWidget)
        generate_widget.close_dialog.connect(self.close)
        self.stacked_widget.addWidget(generate_widget)

        existing_config_widget = ExistingConfigWidget()
        existing_config_widget.change_widget.connect(self.changeWidget)
        existing_config_widget.close_dialog.connect(self.close)
        self.stacked_widget.addWidget(existing_config_widget)

        existing_data_widget = ExistingDataWidget()
        existing_data_widget.change_widget.connect(self.changeWidget)
        existing_data_widget.close_dialog.connect(self.close)
        self.stacked_widget.addWidget(existing_data_widget)

    @pyqtSlot(int)
    def changeWidget(self, index: int) -> None:
        """
        Changes the widget to the one with the given index.
        This is used as a slot for the individual widgets to notify the ConfigDialog that they want to change to another widget.

        :param index: The index of the widget to change to
        """
        self.stacked_widget.setCurrentIndex(index)

class BaseWidget(QWidget):
    """
    This is a base class for all the widgets that are used in the ConfigWidget
    It contains some signals and an index identifying the widget
    """

    change_widget = pyqtSignal(int)
    close_dialog = pyqtSignal(bool)

    def __init__(self, index: int):
        super().__init__()

        self.index = index

class VerticalWidget(BaseWidget):
    """
    This class is a base class for all the widgets that are used in the ConfigWidget that have a vertical layout.
    """
    def __init__(self, index: int):
        super().__init__(index)

        self.layout = QVBoxLayout(self)

    def addNavButton(self, text: str, index: int) -> None:
        """
        Adds a button to the layout that changes the widget to the one with the given index when clicked

        :param text: The text of the button
        :param index: The index the button should change to
        """
        button = QPushButton(text)
        button.clicked.connect(lambda: self.change_widget.emit(index))

        self.layout.addWidget(button)

class VerticalInputWidget(VerticalWidget):
    """
    This class is a base class for all the widgets that are used in the ConfigWidget that have a vertical layout and contain input fields.
    """
    def __init__(self, index: int, title: str=''):
        super().__init__(index)

        self.input_layout = QFormLayout()
        self.input_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self.input_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        self.input_layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft)
        self.title = QLabel(title)

        self.layout.addWidget(self.title)
        self.layout.addLayout(self.input_layout)

    def addFileInput(self, placeholder: str='', dialog_text: str='Select File', filter: str='', directory: str='') -> Tuple[QPushButton, QLineEdit]:
        """
        Adds a file input consisting of a button and a lineedit to the input_layout.
        The button opens a file dialog on click to get a file path and the lineedit shows the path of the selected file.

        :param placeholder: The placeholder text of the lineedit
        :param dialog_text: The window title of the file dialog
        :param directory: The directory the file dialog should open in
        :param filter: The filter of the file dialog
        :return: The button and the lineedit
        """
        line_edit = QLineEdit()
        line_edit.setPlaceholderText(placeholder)
        line_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        def handleButtonClick():
            file_name, _ = QFileDialog.getOpenFileName(self, dialog_text, directory, filter)
            line_edit.setText(file_name)

        button = QPushButton(QIcon(f'{ROOT_PATH}/gui/icons/FolderIcon.svg'), '')
        button.clicked.connect(handleButtonClick)


        self.input_layout.addRow(button, line_edit)

        return button, line_edit

    def addDirectoryInput(self, placeholder: str='', dialog_text: str='Select Directory') -> Tuple[QPushButton, QLineEdit]:
        """
        Adds a directory input consisting of a button and a lineedit to the input_layout.
        The button opens a directory dialog on click to get a directory path and the lineedit shows the path of the selected directory.

        :param placeholder: The placeholder text of the lineedit
        :param dialog_text: The window title of the file dialog
        :return: The button and the lineedit
        """
        line_edit = QLineEdit()
        line_edit.setPlaceholderText(placeholder)
        line_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        def handleButtonClick():
            directory = QFileDialog.getExistingDirectory(self, dialog_text)
            line_edit.setText(directory)

        button = QPushButton(QIcon(f'{ROOT_PATH}/gui/icons/FolderIcon.svg'), '')
        button.clicked.connect(handleButtonClick)

        self.input_layout.addRow(button, line_edit)

        return button, line_edit

class InitialWidget(VerticalWidget):
    """
    This is the widget that is shown initially when the user opens the ConfigDialog.
    """
    def __init__(self):
        super().__init__(INITIAL_WIDGET)

        self.layout.addWidget(QLabel('In this window you can setup the collection of images and a corresponding config file that will be used for the application.\nNote: You may need to restart the application for the changes to take effect.'))
        self.addNavButton('Generate new link to your collection', GENERATE_WIDGET)
        # self.addNavButton('Use existing config file', EXISTING_CONFIG_WIDGET)
        self.addNavButton('Use existing data', EXISTING_DATA_WIDGET)

class GenerateWidget(VerticalInputWidget):
    """
    This is the widget that is shown when the user wants to generate a new config file.
    In this widget the user can provide the path to the folder containing the images and optionally a file containing the meta data
    and generate a new dataset and config file from these.
    """
    def __init__(self):
        super().__init__(GENERATE_WIDGET)

        _, self.images_dir_line_edit = self.addDirectoryInput(placeholder='Path to the folder containing the images',
                                                              dialog_text='Select the images directory')
        _, self.meta_file_line_edit = self.addFileInput(placeholder='Path to the file containing the meta data (optional)',
                                                        dialog_text='Select the meta data file',
                                                        filter='META data file (*xlsx *csv)')

        self.name_line_edit = QLineEdit()
        self.name_line_edit.setPlaceholderText('Name of the dataset (optional)')
        self.name_line_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self.generate_button = QPushButton('Generate')
        self.generate_button.clicked.connect(self.handleGenerateClick)

        self.title.setText('Provide the path to the folder containing the images and optionally a file containing the meta data.')
        self.input_layout.addRow(QPushButton().hide(), self.name_line_edit)
        self.layout.addWidget(self.generate_button)
        self.addNavButton('Back', INITIAL_WIDGET)

    def checkInputs(self) -> bool:
        """
        Checks if the inputs are valid

        :return: True if the inputs are valid, False otherwise
        """
        images_dir = self.images_dir_line_edit.text()
        meta_file = self.meta_file_line_edit.text()

        # Check if the images directory is valid
        if not os.path.isdir(images_dir):
            showError('Invalid Path', 'The path to the images directory is not valid')
            return False

        # If a meta file is given check if it is valid
        if meta_file and not os.path.isfile(meta_file):
            showError('Invalid Path', 'The path to the meta file is not valid')
            return False

        return True

    def handleGenerateClick(self) -> None:
        """
        This method is called when the generate button is clicked.
        It checks if the paths are valid and if so generates a dataset and a config file.

        If this is successful it emits the close signal to close the dialog.
        """
        if not self.checkInputs():
            return

        images_dir = self.images_dir_line_edit.text()
        meta_file = self.meta_file_line_edit.text()
        name = self.name_line_edit.text()
        output_dir = f'{ROOT_PATH}/dataset'

        # Set default name if none is given
        if not name:
            name = 'dataset'

        if meta_file:
            # Try to preprocess the meta file
            try:
                default_preprocessing(meta_file, images_dir, f'{output_dir}/{name}_meta_data.csv')
            except:
                copyFile(meta_file, f'{output_dir}/{name}_meta_data.csv')
        else:
            # If no meta file is given create an empty one
            # Since the search requires a meta file containing an "encoding_id" we add a dummy one
            empty_meta_file = open(f'{output_dir}/{name}_meta_data.csv', 'w')
            empty_meta_file.write('encoding_id\n-1')
            empty_meta_file.close()

        # Create the config file
        json.dump({
            'info_path': f'{output_dir}/{name}_info.hdf5',
            'encodings_path': f'{output_dir}/{name}_CLIP.hdf5',
            'meta_path': f'{output_dir}/{name}_meta_data.csv'},
            open(f'{ROOT_PATH}/dataset/config.json', 'w'))

        # Create the progress bar
        self.progress_bar = QProgressDialog(self)
        self.progress_bar.setCancelButton(None)
        self.progress_bar.setWindowTitle('Generating Dataset')
        self.progress_bar.show()

        # Delete old dataset if it exists
        if os.path.isfile(f'{output_dir}/{name}_info.hdf5'):
            os.remove(f'{output_dir}/{name}_info.hdf5')
        if os.path.isfile(f'{output_dir}/{name}_CLIP.hdf5'):
            os.remove(f'{output_dir}/{name}_CLIP.hdf5')

        # Use a thread to generate the dataset so the progress bar can be updated while generating
        # Otherwise the generate script would block the QT event loop
        # It is also necessary to store it in self, so it does not get garbage collected
        self.generate_thread = GenerateThread(images_dir, f'{output_dir}/', batch_size=50, output_name=name)
        self.generate_thread.starting.connect(self.progress_bar.setMaximum)
        self.generate_thread.valueChanged.connect(self.progress_bar.setValue)
        self.generate_thread.finished.connect(self.close_dialog.emit)
        self.generate_thread.start()

class ExistingConfigWidget(VerticalInputWidget):
    """
    This is the widget that is shown when the user wants to use an existing config file.
    It asks the user to provide the path to the config file and copies it to the root directory.
    """
    def __init__(self):
        super().__init__(EXISTING_CONFIG_WIDGET)

        _, self.config_file_line_edit = self.addFileInput(placeholder='Path to the config file',
                                                          dialog_text='Select the config file', filter='*.json')

        self.confirm_button = QPushButton('Confirm')
        self.confirm_button.clicked.connect(self.handleConfirmClick)

        self.title.setText('Provide the path to the config file.')
        self.layout.addWidget(self.confirm_button)
        self.addNavButton('Back', INITIAL_WIDGET)

    def handleConfirmClick(self) -> None:
        """
        This method is called when the confirm button is clicked.
        It checks if the path is valid and if so copies the config file and emits the close signal to close the dialog.
        """
        config_file = self.config_file_line_edit.text()

        if not os.path.isfile(config_file):
            showError('Invalid Path', 'The path to the config file is not valid')
            return

        copyFile(config_file, f'{ROOT_PATH}/dataset/config.json')

        self.close_dialog.emit(True)

class ExistingDataWidget(VerticalInputWidget):
    """
    This is the widget that is shown when the user wants to use existing data.
    It asks for the paths to the info, encodings and metadata file and generates a config file referencing these files.
    """
    def __init__(self):
        super().__init__(EXISTING_DATA_WIDGET)

        _, self.encodings_file_line_edit = self.addFileInput(placeholder='Path to the encodings file',
                                                             dialog_text='Select the encodings file', filter='*.hdf5',
                                                            directory=f'{ROOT_PATH}/dataset')
        _, self.info_file_line_edit = self.addFileInput(placeholder='Path to the info file',
                                                        dialog_text='Select the info file', filter='*.hdf5',
                                                        directory=f'{ROOT_PATH}/dataset')
        _, self.meta_file_line_edit = self.addFileInput(placeholder='Path to the file containing the meta data (optional)',
                                                        dialog_text='Select the meta data file',
                                                        filter='META data file (*xlsx *csv)')

        self.confirm_button = QPushButton('Confirm')
        self.confirm_button.clicked.connect(self.handleConfirmClick)

        self.title.setText('Provide the paths to the encoding, info and meta data file.')
        self.layout.addWidget(self.confirm_button)
        self.addNavButton('Back', INITIAL_WIDGET)

    def checkInputs(self) -> bool:
        """
        Checks if the inputs are valid

        :return: True if the inputs are valid, False otherwise
        """
        info_file = self.info_file_line_edit.text()
        encodings_file = self.encodings_file_line_edit.text()
        meta_file = self.meta_file_line_edit.text()

        if not os.path.isfile(info_file):
            showError('Invalid Path', 'The path to the info file is not valid')
            return False

        if not os.path.isfile(encodings_file):
            showError('Invalid Path', 'The path to the encodings file is not valid')
            return False

        if meta_file and not os.path.isfile(meta_file):
            showError('Invalid Path', 'The path to the meta data file is not valid')
            return False

        return True

    def handleConfirmClick(self) -> None:
        """
        This method is called when the confirm button is clicked.
        It checks if the inputs are valid and if so copies the files, creates the config file
        and emits the close signal to close the dialog.
        """
        self.checkInputs()

        info_file = self.info_file_line_edit.text()
        encodings_file = self.encodings_file_line_edit.text()
        meta_file = self.meta_file_line_edit.text()
        output_dir = f'{ROOT_PATH}/dataset'
        name = 'dataset'

        # Copy the files to the output directory
        copyFile(info_file, f'{output_dir}/{name}_info.hdf5')
        copyFile(encodings_file, f'{output_dir}/{name}_CLIP.hdf5')

        if meta_file:
            # Copy the meta file to the output directory
            copyFile(meta_file, f'{output_dir}/{name}_meta_data.csv')
        else:
            # If no meta file is given create an empty one
            # Since the search requires a meta file containing an "encoding_id" we add a dummy one
            empty_meta_file = open(f'{output_dir}/{name}_meta_data.csv', 'w')
            empty_meta_file.write('encoding_id\n-1')
            empty_meta_file.close()

        # Create the config file
        json.dump({
            'info_path': f'{output_dir}/{name}_info.hdf5',
            'encodings_path': f'{output_dir}/{name}_CLIP.hdf5',
            'meta_path': f'{output_dir}/{name}_meta_data.csv'},
            open(f'{ROOT_PATH}/dataset/config.json', 'w'))

        self.close_dialog.emit(True)

class GenerateThread(QThread):
    """
    This class is used to generate the dataset in a separate thread.
    This is necessary so the progress bar can be updated while generating the dataset.
    """

    starting = pyqtSignal(int)
    finished = pyqtSignal(bool)
    valueChanged = pyqtSignal(int)

    def __init__(self, images_dir: str, output_dir: str, batch_size: int, output_name: str):
        super().__init__()

        self.images_dir = images_dir
        self.output_dir = output_dir
        self.batch_size = batch_size
        self.output_name = output_name

    def run(self) -> None:
        """
        This method is called when the thread is started.
        It just calls the generate_dataset function from the generate script.
        """
        generate_dataset(image_dir=self.images_dir,
                         output_dir=self.output_dir,
                         batch_size=self.batch_size,
                         output_name=self.output_name,
                         thread=self)
