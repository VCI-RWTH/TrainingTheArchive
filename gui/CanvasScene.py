from random import uniform
from typing import List, Dict, Any

from PyQt6.QtWidgets import QGraphicsScene, QGraphicsSceneMouseEvent, QGraphicsSceneDragDropEvent, QGraphicsTextItem
from PyQt6.QtCore import Qt, QPointF, QRectF, pyqtSlot
from PyQt6.QtGui import QTransform, QKeyEvent, QPainter, QFont

from gui.Box import Box
from gui.Group import Group
from gui.HandleGraphicsItem import *
from gui.ImageGraphicsItem import ImageGraphicsItem
from gui.Note import Note, NoteWidget
from gui.PreviewWindow import PreviewWindow


class CanvasScene(QGraphicsScene):
    """
    The "main" canvas class. It contains all the items that are on the canvas and handles all the logic for the items.
    """

    scene_width = 64000
    scene_height = 64000

    def __init__(self):
        super().__init__()

        # artsearch, search_bar, history are set by the main window after the canvas is created
        self.artsearch = None
        self.search_bar = None
        self.history = None

        # The box is the area where the images that are removed from the canvas will go and act as negative examples
        self.box = Box()
        self.box.image_double_clicked.connect(self.addImage)
        self.box.add_context_menu_triggered.connect(self.addImage)

        # Create the disclaimer text
        self.addItem(self.createDisclaimer())

        # The Parameter of the PreviewWindow is later correctly set by the MainWindow after the canvas is created
        # Since we want only one PreviewWindow for all images on the canvas we define it here and update the image
        # when the user clicks on an image
        self.preview_window = PreviewWindow(None)

        # Set the scene size
        self.setSceneRect(-self.scene_width // 2, -self.scene_height // 2, self.scene_width, self.scene_height)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """
        Override the mousePressEvent to clear the selection when the user clicks on an empty space or an unselectable item.
        """
        if event.button() == Qt.MouseButton.LeftButton:
            item = self.itemAt(event.scenePos(), QTransform())
            if item and isinstance(item, Handle):
                self.clearSelection()

        super().mousePressEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """
        Override the keyPressEvent to delete the selected items when the user presses the delete or backspace key.
        """
        if event.key() == Qt.Key.Key_Delete or event.key() == Qt.Key.Key_Backspace:
            for item in self.selectedItems():
                if isinstance(item, HandleGraphicsItem):
                    item.remove()
                else:
                    item.prepareGeometryChange()
                    self.removeItem(item)

            self.update()

        super().keyPressEvent(event)

    def dragEnterEvent(self, event: QGraphicsSceneDragDropEvent) -> None:
        """
        Override the dragEnterEvent to only a drag from an image.
        Since the image_id is used for drag & drop only accept the drag if the mimeData contains a number.
        """
        if event.mimeData().hasFormat('text/plain'):
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QGraphicsSceneDragDropEvent) -> None:
        """
        Override the dragMoveEvent to only a drag from an image.
        Since the image_id is used for drag & drop only accept the drag if the mimeData contains a number.
        """
        if event.mimeData().hasFormat('text/plain'):
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event: QGraphicsSceneDragDropEvent) -> None:
        """
        Override the dropEvent to only a drag from an image.
        If an image was dropped create a new image item and place it where it was dropped.

        The mime data for this application is a simple string with the format 'type:content'
        """
        if event.mimeData().hasFormat('text/plain'):
            text = event.mimeData().text()
            type = text.split(':')[0]

            if type == 'image':
                image_id = int(text.split(':')[1])
                image = self.createImage(image_id, self.artsearch.getImagePath(image_id))
                image.setPos(event.scenePos() -
                             QPointF(image.boundingRect().width() / 2, image.boundingRect().height() / 2) -
                             QPointF(image.getHandleSize(), image.getHandleSize()))
                self.addImage(image)
            elif type == 'note':
                content = text.split(':')[1]
                color = text.split(':')[2]

                note = self.createNote()
                note.setContent(content)
                note.setColor(color)
                note.setPos(event.scenePos() -
                             QPointF(note.boundingRect().width() / 2, note.boundingRect().height() / 2) -
                             QPointF(note.getHandleSize(), note.getHandleSize()))
                self.addItem(note)
                self.box.removeNoteByContent(content)

                self.history.addTimeStamp()

    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:
        """
        Override the drawBackground to draw the background of the canvas.
        """
        super().drawBackground(painter, rect)

        # Test if the scene is empty and draw the disclaimer text if it is
        # Since the text itself
        if len(self.items()) <= 1:
            pos = rect.center()
            pos -= QPointF(self.disclaimer_text.boundingRect().width() / 2,
                           self.disclaimer_text.boundingRect().height() / 2)

            self.disclaimer_text.setPos(pos)
            self.disclaimer_text.show()
        else:
            self.disclaimer_text.hide()



    @pyqtSlot(QGraphicsItem)
    def itemMoved(self, item: HandleGraphicsItem) -> None:
        """
        Slot that is called when an item on the canvas is moved.
        """
        self.updateGroups()

        if isinstance(item, Group):
            for image in item.getImages():
                image.checkForGroupNameOverlap()

        self.history.addTimeStamp()

    @pyqtSlot(QGraphicsItem)
    def itemScaled(self, item: HandleGraphicsItem) -> None:
        """
        Slot that is called when an item on the canvas is scaled.
        """
        self.updateGroups()

        if isinstance(item, Group):
            for image in item.getImages():
                image.checkForGroupNameOverlap()

        self.history.addTimeStamp()

    def clear(self) -> None:
        super().clear()

        # Add new disclaimer text because the reference to the old one is lost when the scene is cleared
        self.addItem(self.createDisclaimer())


    def createImage(self, image_id: int, path: str) -> ImageGraphicsItem:
        """
        Creates a new ImageGraphicsItem with the given image_id and path to be used on the canvas.
        Since we allow custom images which do not have an image_id we need the id and the path to the image.

        :param image_id: The id of the image
        :param path: The path of the image file
        :return: The created ImageGraphicsItem object
        """
        image = ImageGraphicsItem(image_id, path, self.artsearch)

        return image

    @pyqtSlot(int)
    def addImage(self, image) -> None:
        """
        Adds an image to the canvas.
        If the image is only an image_id it is added to the middle of the canvas.
        When the center is already occupied the image is moved to a random free spot near the center.

        If the image is an ImageGraphicsItem it is added to the canvas at the position it is currently at.

        :param image: The image to add (either an image_id or an ImageGraphicsItem)
        """
        if isinstance(image, int):
            # If only an image id is given, create a new image item in the middle of the view
            image = self.createImage(image, self.artsearch.getImagePath(image))
            self.placeInViewCenter(image)

            # Get all images that are colliding with the new image
            colliding_items = [image for image in self.collidingItems(image) if isinstance(image, ImageGraphicsItem) or isinstance(image, Group)]

            # If there are colliding images move the new image to a random free spot near the center
            if colliding_items:

                # Determine the direction in which the image should be moved by calculating the average difference
                # between the new image and the colliding images and using the direction of the difference as the
                # direction in which the image should be moved
                average_difference = QPointF()
                for colliding_image in colliding_items:
                    average_difference += (colliding_image.pos() - image.pos()) / len(colliding_items)

                max_difference = max(abs(average_difference.x()), abs(average_difference.y()))

                x_move_factor = - average_difference.x() / max_difference
                y_move_factor = - average_difference.y() / max_difference

                if x_move_factor == 0:
                    x_move_factor = uniform(-1, 1)
                if y_move_factor == 0:
                    y_move_factor = uniform(-1, 1)

                # Move the image in the determined direction until it is not colliding with any other images anymore
                # or until 50 attempts have been made
                attempts = 0
                while colliding_items:
                    image.moveBy(x_move_factor * 40, y_move_factor * 40)

                    attempts += 1
                    if attempts > 50:
                        break

                    colliding_items = [item for item in self.collidingItems(image) if isinstance(item, ImageGraphicsItem) or isinstance(item, Group)]

        self.addItem(image)

        # Since the image is added to the canvas it can no longer be in the box or search bar and its weight is positive
        self.search_bar.removeImage(image.id)
        self.box.removeImage(image.id)
        self.artsearch.setImagePositive(image.id)

        self.update()
        self.updateGroups()

        self.search_bar.updateResults()
        self.history.addTimeStamp()

    def addCustomImage(self, path: str) -> None:
        """
        Adds a custom image to the canvas.
        Note that since the image is not in the embedding it can not influence the search.

        :param path: The path to the image file that should be added
        """
        image = self.createImage(-1, path)
        self.placeInViewCenter(image)

        self.addItem(image)
        self.update()

    def removeImage(self, image: ImageGraphicsItem) -> None:
        """
        Removes an image from the canvas.
        If the image is not a custom image it is added to the box and its weight is set to negative.

        :param image: The image to remove. Must be an ImageGraphicsItem not an image_id
        :return:
        """
        image.prepareGeometryChange()
        self.removeItem(image)

        # Check if the image is a custom image
        if image.id != -1:
            self.artsearch.setImageNegative(image.id)
            self.box.addImage(image.id)
            self.shakeBox()

        self.update()
        self.updateGroups()

        self.search_bar.updateResults()
        self.history.addTimeStamp()

    def createGroup(self) -> Group:
        """
        Creates a new group object that can be added to the canvas.

        :return: The newly created group object
        """
        group = Group()

        return group

    def addGroup(self) -> None:
        """
        Adds a new group to the canvas.

        If there are selected items the group is created around the selected items.
        Otherwise, the group is created in the middle of the canvas.

        The name of the group is set to the last search term, if there is one.
        """
        group = self.createGroup()
        self.addItem(group)

        # Set the name of the group
        last_search_term = self.search_bar.getLastSearchTerm()
        if last_search_term:
            group.setName(last_search_term)
        else:
            group.setName('New Group')

        # If there are selected items create the group around the selected items
        if self.selectedItems():
            rect = QRectF()

            # Get the bounding rectangle of all selected items
            for item in self.selectedItems():
                rect = rect.united(item.sceneBoundingRect())

            # Set the position and size of the group to fit the bounding rectangle of the selected items
            group.setPos(rect.topLeft() - QPointF(group.getHandleSize(),
                                                  group.getHandleSize() + group.group_name.boundingRect().height()))
            group.handles[BOTTOM_RIGHT].setPos(rect.width() + group.getHandleSize() * 2,
                                               rect.height() + group.getHandleSize() * 2 + group.group_name.boundingRect().height())

            group.normalizeHandles()
            group.group_name.updateSize()
        else:
            # Create group in the center of the view
            self.placeInViewCenter(group)

        # Since the group should influence the search we add it to the search
        self.artsearch.create_group(group)

        self.update()
        self.updateGroups()

        self.search_bar.updateResults()
        self.history.addTimeStamp()

    def removeGroup(self, group: Group) -> None:
        """
        Removes a group from the canvas.
        """
        group.prepareGeometryChange()
        self.removeItem(group)

        self.artsearch.remove_group(group)

        self.update()
        self.updateGroups()

        self.search_bar.updateResults()
        self.history.addTimeStamp()

    def createNote(self) -> Note:
        """
        Creates a new note object that can be added to the canvas.
        """
        note = Note()

        return note

    def addNote(self) -> None:
        """
        Adds a new note to the canvas.
        Since notes can only be added from the toolbar the note is created in the middle of the canvas.
        """
        note = self.createNote()
        self.placeInViewCenter(note)

        self.addItem(note)
        self.update()
        self.history.addTimeStamp()

    def removeNote(self, note: Note) -> None:
        """
        Removes a note from the canvas.

        :param note: The note object to remove
        """
        # Add note to box
        note_text = note.content.toPlainText()
        note_color = note.brush.color()

        note_widget = NoteWidget(note_text, note_color)
        self.box.addWidget(note_widget)

        # Remove note from canvas
        note.prepareGeometryChange()
        self.removeItem(note)
        self.update()
        self.history.addTimeStamp()

    def favorite(self) -> None:
        """
        Flips the favorite flag of all selected images
        """
        if self.selectedItems():
            for item in self.selectedItems():
                if isinstance(item, ImageGraphicsItem):
                    item.favorite = not item.favorite
                    item.setOpacity(1)
                    item.update()

            self.history.addTimeStamp()

    def shakeBox(self) -> None:
        # Since this is the only place where the box button is used we access it using this "hacky" way
        self.views()[0].parent().parent().box_button.shake_animation.start()

    def updateGroups(self) -> None:
        """
        Updates the groups in the search.
        This should be called whenever the content of a group changes or a group is added/removed
        to make sure the search is up-to-date.
        """
        images = self.getImages()

        for group in self.getGroups():
            # Set the images in the group as positive and all other images as negative
            positive = [image.id for image in group.getContent() if isinstance(image, ImageGraphicsItem)]
            negative = [image.id for image in images if image.id not in positive]

            self.artsearch.updateGroup(group, positive, negative)

        # self.artsearch.update()
        self.artsearch.content_change()

    def toggleNotes(self) -> None:
        """
        Toggles the opacity of all notes.
        """
        for note in self.getNotes():
            if note.opacity() == 1:
                note.setOpacity(0.2)
            else:
                note.setOpacity(1)
        self.update()

    def toggleNonFavorites(self) -> None:
        """
        Toggles the opacity of all non-favorite images.
        """
        for image in self.getImages():
            if not image.favorite and image.opacity() == 1:
                image.setOpacity(0.2)
            else:
                image.setOpacity(1)

        self.update()

    def getImages(self) -> List[ImageGraphicsItem]:
        return [item for item in self.items() if isinstance(item, ImageGraphicsItem)]

    def getGroups(self) -> List[Group]:
        return [item for item in self.items() if isinstance(item, Group)]

    def getNotes(self) -> List[Note]:
        return [item for item in self.items() if isinstance(item, Note)]

    def getMaxImageZValue(self) -> float:
        """
        Returns the highest z value of all images on the canvas.
        """
        return max([image.zValue() for image in self.getImages()])

    def getMinImageZValue(self) -> float:
        """
        Returns the lowest z value of all images on the canvas.
        """
        return min([image.zValue() for image in self.getImages()])

    def createDisclaimer(self) -> QGraphicsTextItem:
        """
        Creates the disclaimer text that is displayed when the canvas is empty.

        :return: The created QGraphicsTextItem object
        """
        self.disclaimer_text = QGraphicsTextItem('Drop Images Here')
        self.disclaimer_text.setDefaultTextColor(Qt.GlobalColor.gray)
        self.disclaimer_text.setFont(QFont('Arial', 50))

        if self.views():
            self.placeInViewCenter(self.disclaimer_text)

        return self.disclaimer_text

    def getViewCenter(self) -> QPointF:
        view = self.views()[0]
        return view.mapToScene(view.rect().center())

    def placeInViewCenter(self, item: QGraphicsItem) -> None:
        """
        Places an item in the center of the view.

        :param item: The item to place
        """
        if isinstance(item, HandleGraphicsItem):
            item.setPos(self.getViewCenter() -
                        QPointF(item.boundingRect().width() / 2, item.boundingRect().height() / 2) -
                        QPointF(item.getHandleSize() / 2, item.getHandleSize() / 2))
        else:
            item.setPos(self.getViewCenter() -
                        QPointF(item.boundingRect().width() / 2, item.boundingRect().height() / 2))

    def serialize(self) -> Dict[str, Any]:
        """
        Serializes the scenes contents into a dictionary

        :return: The serialized content in the form of a dictionary
        """
        groups = []
        notes = []
        images = []

        for item in self.items():
            if isinstance(item, Group):
                groups.append(item.serialize())
            elif isinstance(item, Note):
                notes.append(item.serialize())
            elif isinstance(item, ImageGraphicsItem):
                images.append(item.serialize())

        return {
            'groups': groups,
            'notes': notes,
            'images': images,
            'box': self.box.serialize()
        }

    def deserialize(self, data: Dict[str, Any]) -> None:
        """
        Deserializes the given data into the scene

        :param data: The data to deserialize
        """
        self.clear()

        for image_data in data['images']:
            image = ImageGraphicsItem(image_data['id'], image_data['path'], self.artsearch)
            image.setPos(image_data['x'], image_data['y'])
            image.handles[BOTTOM_RIGHT].setPos(image_data['bottom_right']['x'],
                                               image_data['bottom_right']['y'])
            image.favorite = image_data['favorite']
            image.setZValue(image_data['z_value'])

            image.updatePixmapSize()
            image.placeHandles()
            image.normalizeHandles()

            self.addItem(image)

            self.search_bar.removeImage(image.id)
            self.artsearch.setImagePositive(image.id)

        for group_data in data['groups']:
            group = self.createGroup()
            group.setPos(group_data['x'], group_data['y'])
            group.handles[BOTTOM_RIGHT].setPos(group_data['bottom_right']['x'],
                                               group_data['bottom_right']['y'])
            group.setName(group_data['name'])
            group.setColor(group_data['color'])

            group.normalizeHandles()

            self.addItem(group)
            self.artsearch.create_group(group)

        for note_data in data['notes']:
            note = self.createNote()
            note.setPos(note_data['x'], note_data['y'])
            note.handles[BOTTOM_RIGHT].setPos(note_data['bottom_right']['x'],
                                              note_data['bottom_right']['y'])
            note.setContent(note_data['content'])
            note.setColor(note_data['color'])

            note.normalizeHandles()

            self.addItem(note)

        self.box.deserialize(data['box'])

        # Add new disclaimer text because the reference to the old one is lost when the scene is cleared
        self.addItem(self.createDisclaimer())

        self.update()
