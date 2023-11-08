from typing import Dict, Any

from PyQt6.QtCore import QTimer

class History:
    """
    Class that handles the history of the application.
    It stores the states/timestamps of the relevant objects (search bar, canvas, artsearch) and allows to undo/redo changes
    For this purpose, it stores a list of timestamps and the current index in that list.
    Each class that should be stored in the history needs to implement the serialize() and deserialize() methods.
    """

    size = 10

    def __init__(self, search_bar, scene, artsearch):
        # Store references to the objects that should be stored in the history to get their states
        self.search_bar = search_bar
        self.scene = scene
        self.artsearch = artsearch

        self.history = [] # List of timestamps
        self.current_index = -1

        # Lock to prevent spamming the history
        self.undo_redo_lock = False

    def undo(self) -> None:
        """
        Undo a change if possible
        """
        if self.current_index > 0 and not self.undo_redo_lock:
            self.current_index -= 1
            self.restoreTimeStamp(self.current_index)

            # Disable the undo and redo action for 1 second, while the undo/redo action is being executed
            self.undo_redo_lock = True
            QTimer.singleShot(1000, lambda: setattr(self, 'undo_redo_lock', False))

    def redo(self) -> None:
        """
        Redo a change if possible
        """
        if self.current_index + 1 < len(self.history) and not self.undo_redo_lock:
            self.current_index += 1
            self.restoreTimeStamp(self.current_index)

            # Disable the undo and redo action for 1 second, while the undo/redo action is being executed
            self.undo_redo_lock = True
            QTimer.singleShot(1000, lambda: setattr(self, 'undo_redo_lock', False))

    def createTimeStamp(self) -> Dict[str, Dict[str, Any]]:
        """
        Takes a snapshot of the current state of the relevant objects and returns it as a dictionary

        :return: The state of the application as a dictionary of serialized objects
        """
        return {
            'search_bar': self.search_bar.serialize(),
            'canvas': self.scene.serialize(),
            'artsearch': self.artsearch.serialize()
        }

    def addTimeStamp(self) -> None:
        """
        Adds the current state of the application to the history.
        If there are timestamps after the current one, they are deleted/overwritten
        If the maximum number of timestamps is exceeded, the oldest one is deleted
        """
        # Delete all timestamps that come after the current one if there are any
        if self.current_index + 1 < len(self.history):
            self.history = self.history[0:self.current_index + 1]

        # Delete old changes if the maximum is exceeded
        if self.current_index + 1 >= self.size:
            self.history = self.history[1:]
            self.current_index -= 1

        self.history.append(self.createTimeStamp())
        self.current_index += 1

    def popTimeStamp(self) -> None:
        """
        Deletes the newest timestamp if there is one
        """
        if len(self.history) > 0:
            self.history.pop()
            self.current_index -= 1

    def restoreTimeStamp(self, index: int) -> None:
        """
        Restores the state of the application to the state of the timestamp at the given index
        by deserializing the objects

        :param index: The index of the timestamp in the history array, that should be restored
        """
        # Check if index is valid
        if index < 0 or index >= len(self.history):
            return

        # It is important to deserialize artsearch before scene to add groups properly to artsearch
        self.artsearch.deserialize(self.history[index]['artsearch'])
        self.search_bar.deserialize(self.history[index]['search_bar'])
        self.scene.deserialize(self.history[index]['canvas'])

    def reset(self) -> None:
        """
        Resets the history by deleting all timestamps
        """
        self.history = []
        self.current_index = -1

    def printDebugInfo(self) -> None:
        """
        Prints debug information about the history to the console
        """
        print('History:')
        print(f'Current index: {self.current_index}/{len(self.history) - 1}')
        for i, time_stamp in enumerate(self.history):
            print(f'{"->" if i == self.current_index else "  "} Index {i}: {time_stamp}')
        print()
