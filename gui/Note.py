from typing import Dict, Any

from PyQt6.QtWidgets import QGraphicsTextItem, QGraphicsSceneMouseEvent, QColorDialog, QLabel, QApplication
from PyQt6.QtCore import Qt, QPointF, QRectF, QMimeData
from PyQt6.QtGui import QBrush, QPen, QColor, QPainterPath, QFont, QResizeEvent, QContextMenuEvent, QCursor, QMouseEvent, QDrag

from gui.HandleGraphicsItem import *


class Note(HandleGraphicsItem):
    """
    This is a note that can be placed on the canvas it contains a text field where the user can enter text.
    As a subclass from HandleGraphicsItem it is able to be resized by dragging its handles/corner
    """
    def __init__(self):
        super().__init__()

        self.brush = QBrush(QColor('#FFFF99'))
        self.pen.setColor(QColor('#FFFF99').darker(150))
        self.setHandlesVisible(False)
        self.setZValue(0 + 9999)

        # Create the actual note content which is a QGraphicsTextItem to allow for text editing
        # The content is a child of the top left handle so that it moves with the note
        self.content = NoteContent(self.handles[TOP_LEFT])
        self.content.setPos(QPointF(self.getHandleSize() + 5, self.getHandleSize() + 5))
        self.content.setPlainText('New Note')
        self.content.updateSize()

    def initContextMenu(self) -> None:
        """
        Extend the context menu with the option to change the color of the note
        """
        super().initContextMenu()

        self.change_color_action = self.context_menu.addAction('Change Color')
        self.change_color_action.triggered.connect(self.setCustomColor)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """
        When the user releases the mouse/finishes moving the note check if the note overlaps with any other notes
        """
        super().mouseReleaseEvent(event)

        self.checkForGroupNameOverlap()

    def handleMoving(self, position: int, event: QGraphicsSceneMouseEvent) -> None:
        """
        When a handle of the note moves (the note is resized) update the size of the note content
        """
        super().handleMoving(position, event)

        self.content.updateSize()

    def remove(self) -> None:
        """
        Override remove to remove the note properly from the scene
        """
        if self.scene():
            self.scene().removeNote(self)

    def setContent(self, content: str) -> None:
        """
        Set the content/text of the note and update its size to adjust for the new content if necessary
        """
        self.content.setPlainText(content)
        self.content.updateSize()

    def setColor(self, color) -> None:
        """
        Set the color of the note. It also automatically sets the text color to black or white depending on the
        brightness of the color and changes the border to be a darker version of the color

        :param color: The color to set
        """
        if isinstance(color, str):
            color = QColor(color)

        if color.lightnessF() > 0.5:
            self.content.setDefaultTextColor(QColor('#000000'))
        else:
            self.content.setDefaultTextColor(QColor('#FFFFFF'))

        self.brush.setColor(color)
        self.pen.setColor(color.darker(150))
        self.update()

    def setCustomColor(self) -> None:
        """
        Open a color dialog to let the user choose a custom color for the note
        """
        color = QColorDialog.getColor(self.brush.color())
        if color.isValid():
            self.setColor(color)

    def serialize(self) -> Dict[str, Any]:
        super_dict = super().serialize()

        super_dict['content'] = self.content.toPlainText()
        super_dict['color'] = self.brush.color().name()

        return super_dict


class NoteContent(QGraphicsTextItem):
    """
    This is the actual content of the note, which is the text the user can edit
    """
    def __init__(self, parent: Note):
        super().__init__(parent)

        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextEditorInteraction)
        self.setCursor(Qt.CursorShape.IBeamCursor)
        self.setZValue(self.parentItem().zValue() + 1)

    def boundingRect(self) -> QRectF:
        return QRectF(QPointF(0, 0), self.parentItem().parentItem().handles[BOTTOM_RIGHT].pos() -
                      QPointF(self.parentItem().size + 5, self.parentItem().size + 5))

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """
        When the user clicks on the note content, if the content is the default text 'New Note' remove it
        """
        if event.button() == Qt.MouseButton.LeftButton and self.toPlainText() == 'New Note':
            self.setPlainText('')

        super().mousePressEvent(event)

    def updateSize(self) -> None:
        """
        Update the size of the text. This is called whenever the text changes or the note is resized
        """
        self.setTextWidth(self.boundingRect().width())

        font = self.font()
        font.setPixelSize(int(self.boundingRect().height() * 0.8 * 0.15))
        self.setFont(font)


class NoteWidget(QLabel):
    """
    This is a widget representation of a note.
    It is used to display the note in the box after removing it from the canvas
    """
    def __init__(self, content: str, color: QColor):
        super().__init__()

        self.content = content  # The content/text of the note
        self.color = color

        self.initUI()
        self.initContextMenu()

    def initUI(self) -> None:
        self.setText(self.content)

        # Since the note is a widget instead of a graphics item it is styled with style sheets
        style = f"""
        QLabel {{
            background-color: {self.color.name()};
            border: 2px solid {self.color.darker(150).name()};
        }}
        """
        self.setStyleSheet(style)

    def initContextMenu(self) -> None:
        self.context_menu = QMenu()

        delete_action = self.context_menu.addAction('Delete')
        delete_action.triggered.connect(self.remove)

    def resizeEvent(self, event: QResizeEvent) -> None:
        """
        Override the resize event to make sure the note is always square
        """
        super().resizeEvent(event)

        self.setFixedHeight(self.width())

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        self.context_menu.exec(event.globalPos())

        super().contextMenuEvent(event)

    def remove(self) -> None:
        """
        Function to remove the note from the box
        """
        box = self.parent().parent().parent()

        if box:
            box.removeWidget(self)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """
        Start a drag & drop operation when the widget is dragged
        Store the content in the mime data as a string and set the widget as the drag pixmap

        The mime data for this application is a simple string with the format 'type:content'
        """
        mime_data = QMimeData()
        mime_data.setText(f'note:{self.content}:{self.color.name()}')

        drag = QDrag(self)
        drag.setMimeData(mime_data)

        pixmap = self.grab(self.rect())
        drag.setPixmap(pixmap)
        drag.setHotSpot(pixmap.rect().center())

        QApplication.setOverrideCursor(Qt.CursorShape.ClosedHandCursor)
        drag.exec(Qt.DropAction.MoveAction)
        QApplication.restoreOverrideCursor()

        super().mouseMoveEvent(event)
