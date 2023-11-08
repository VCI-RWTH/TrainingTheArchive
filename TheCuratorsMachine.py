import os

ROOT_PATH = os.path.dirname(os.path.abspath(__file__))

from PyQt6.QtWidgets import QApplication, QSplashScreen
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap

# Do not import everything at the top of the file so that the splash screen can be shown while loading the modules

def load_stylesheet(path: str) -> str:
    """
    Loads a qss stylesheet from the given path

    :param path: The path to the stylesheet
    :return: The stylesheet as a string
    """
    styles = open(path, 'r').read()

    for key, value in Colors.items():
        styles = styles.replace(key, value)

    return styles

if __name__ == '__main__':
    # Create the actual app and its main window
    app = QApplication([])

    # Create a splash screen to show while the app is loading
    splash_screen = QSplashScreen(QPixmap(f'{ROOT_PATH}/gui/icons/AppIcon.png'))
    splash_screen.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
    splash_screen.show()

    # Import all the modules that are needed to run the application
    import sys
    import json

    # Set output of the application to log files
    # This has to be done before importing the Artsearch, as it uses print statements and thus crashes when running
    # the program without a console, after building the application.
    sys.stdout = open(f'{ROOT_PATH}/stdout.log', 'w')
    sys.stderr = open(f'{ROOT_PATH}/stderr.log', 'w')

    # Set the app id for Windows to use the correct icon in the taskbar.
    try:
        from ctypes import windll  # Only exists on Windows.

        app_id = 'rwth.version'
        windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except ImportError:
        pass

    from ArtSearch import ArtSearch

    from gui.MainWindow import MainWindow
    from gui.ConfigDialog import ConfigDialog
    from gui.Colors import Colors
    from gui.Util import *
    # Finished importing all modules

    app.setWindowIcon(QIcon(f'{ROOT_PATH}/gui/icons/AppIcon.png'))

    # Load the style sheet
    styles = load_stylesheet(f'{ROOT_PATH}/gui/style.qss')
    app.setStyleSheet(styles)

    # Load the config file to get the paths to the images, metadata, ...
    try:
        config = load_config(f'{ROOT_PATH}/dataset/config.json')
    except:
        # Ask for admin rights to generate the config file
        if sys.platform == 'win32':
            from ctypes import windll
            if not windll.shell32.IsUserAnAdmin():
                windll.shell32.ShellExecuteW(None, "runas", sys.executable, __file__, None, 1)
                sys.exit()

        showError('Invalid Config File', 'The config file either does not exist or is invalid')

        config_dialog = ConfigDialog()
        config_dialog.exec()

        config = load_config(f'{ROOT_PATH}/dataset/config.json')

    artsearch = ArtSearch(config['info_path'], config['encodings_path'], config['meta_path'])

    main_window = MainWindow(artsearch)

    splash_screen.finish(main_window)
    main_window.raise_()
    main_window.activateWindow()
    main_window.showNormal()

    sys.exit(app.exec())