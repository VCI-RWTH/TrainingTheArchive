import os

from PyQt6.QtWidgets import QScrollArea, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap

MAIN_TEXT = """This prototype was developed as part of the research project: 
Training the Archive, 01.01.2020 – 31.12.2023.

A project by Ludwig Forum Aachen in cooperation with HMKV Hartware MedienKunstVerein, Dortmund and the Visual Computing Institute of RWTH Aachen University as Digtial Partner.

Software and interface development: Moritz Ibing, Dr. Isaak Lim, Tim Elsner, Marian Schneider, and Prof. Dr. Leif Kobbelt (Visual Computing Institute, RWTH Aachen University)
Concept and project management: Dominik Bönisch (Ludwig Forum Aachen)
Collaborative partner: Dr. Inke Arns and Dr. Francis Hunger (HMKV Hartware MedienKunstVerein, Dortmund)
Testing and feedback: Eva Birkenstock, Dr. Annette Lagler, Dr. Nora Riediger, Ana Sophie Salazar, and Sonja Benzner (Ludwig Forum Aachen)

The Curator’s Machine is published under a BSD-3 license, October 2023.

This work was funded by the German Research Foundation within the Gottfried Wilhelm Leibniz program."""

END_TEXT = '\nRelated to the software, a technical paper was published at the Efficient Deep Learning for Computer Vision CVPR Workshop 2023:'
MORE_INFORMATION_TEXT = '\nFind more information at:'

PAPER_LINK = 'https://www.graphics.rwth-aachen.de/publication/03349/'
LUFO_LINK = 'https://trainingthearchive.ludwigforum.de'
GITHUB_LINK = 'https://github.com/VCI-RWTH/TrainingTheArchive'

# Useful paths
ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGO_DIR = os.path.join(ROOT_PATH, 'resources', 'images', 'logos')


class AboutWindow(QScrollArea):
    """
    This window is opened when the user clicks on the "About" button in the main window.
    It contains information about the entire project.
    """
    def __init__(self):
        super().__init__()

        self.setWindowTitle('About')
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        self.setWidgetResizable(True)

        self.main_widget = QWidget()
        self.setWidget(self.main_widget)

        self.layout = QVBoxLayout(self.main_widget)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Create texts
        self.main_label = QLabel(MAIN_TEXT, wordWrap=True)
        self.end_label = QLabel(END_TEXT, wordWrap=True)
        self.more_info_label = QLabel(MORE_INFORMATION_TEXT, wordWrap=True)

        # Create links
        def createLink(link: str) -> QLabel:
            label = QLabel(f'<a href="{link}" style="color: black;">{link}</a>')
            label.setOpenExternalLinks(True)
            label.setAlignment(Qt.AlignmentFlag.AlignTop)
            label.setTextFormat(Qt.TextFormat.RichText)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)

            return label

        self.paper_link = createLink(PAPER_LINK)
        self.lufo_link = createLink(LUFO_LINK)
        self.github_link = createLink(GITHUB_LINK)

        # Create logos
        def createLogo(path: str) -> QLabel:
            label = QLabel()
            label.setAlignment(Qt.AlignmentFlag.AlignLeft)

            pixmap = QPixmap(path)
            pixmap = pixmap.scaled(QSize(9999, 45), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

            label.setPixmap(pixmap)
            label.setAlignment(Qt.AlignmentFlag.AlignLeft)
            return label

        self.lufo_logo = createLogo(os.path.join(LOGO_DIR, 'lufo_short.png'))
        self.ksb_logo = createLogo(os.path.join(LOGO_DIR, 'ksb.png'))
        self.bkm_logo = createLogo(os.path.join(LOGO_DIR, 'bkm.png'))
        self.hkmv_logo = createLogo(os.path.join(LOGO_DIR, 'hmkv.png'))
        self.rwth_vci_logo = createLogo(os.path.join(LOGO_DIR, 'rwth_vci.png'))

        self.logo_layout = QGridLayout()
        self.logo_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.logo_layout.setHorizontalSpacing(50)

        self.ksb_layout = QVBoxLayout()
        self.ksb_layout.addWidget(QLabel('Training the Archive is funded by the program'))
        self.ksb_layout.addWidget(self.ksb_logo)
        self.logo_layout.addLayout(self.ksb_layout, 0, 0)

        self.bkm_layout = QVBoxLayout()
        self.bkm_layout.addWidget(QLabel('Funded by'))
        self.bkm_layout.addWidget(self.bkm_logo)
        self.logo_layout.addLayout(self.bkm_layout, 0, 1)

        self.partners_layout = QVBoxLayout()
        self.partners_layout.addWidget(QLabel('Collaborative partners'))
        self.partners_sublayout = QHBoxLayout()
        self.partners_sublayout.setSpacing(50)
        self.partners_sublayout.addWidget(self.lufo_logo)
        self.partners_sublayout.addWidget(self.hkmv_logo)
        self.partners_layout.addLayout(self.partners_sublayout)
        self.logo_layout.addLayout(self.partners_layout, 1, 0)

        self.digital_partner_layout = QVBoxLayout()
        self.digital_partner_layout.addWidget(QLabel('Digital partner'))
        self.digital_partner_layout.addWidget(self.rwth_vci_logo)
        self.logo_layout.addLayout(self.digital_partner_layout, 1, 1)

        # Add widgets to layout
        self.layout.addWidget(self.main_label)
        self.layout.addLayout(self.logo_layout)
        self.layout.addWidget(self.end_label)
        self.layout.addWidget(self.paper_link)
        self.layout.addWidget(self.more_info_label)
        self.layout.addWidget(self.lufo_link)
        self.layout.addWidget(self.github_link)

    def sizeHint(self):
        return QSize(700, 700)

if __name__ == '__main__':
    import sys
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    window = AboutWindow()
    window.show()

    sys.exit(app.exec())