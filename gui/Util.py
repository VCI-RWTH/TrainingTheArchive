import json
import shutil
import os
import pandas as pd

from data import ImageDataset

from PyQt6.QtWidgets import QErrorMessage
from PyQt6.QtCore import QSize
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtGui import QImage, QPainter

BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_config(path: str) -> dict:
    """
    Loads the config from the given path and checks if it contains all necessary keys

    :param path: The path to the config file
    :return: The config as a dictionary
    """
    data = json.load(open(path, 'r'))

    # Check if the config contains the necessary keys
    keys_to_check = ['info_path', 'encodings_path', 'meta_path']

    if not all(key in data for key in keys_to_check):
        raise ValueError(f'Config file at {path} does not contain all necessary keys')

    # Check if the paths are relative and if so replace them with absolute paths
    for key in keys_to_check:
        if not os.path.isabs(data[key]):
            data[key] = os.path.join(BASE_PATH, data[key][2:])

    # Check if all paths actually exist
    for key in keys_to_check:
        if not os.path.exists(data[key]):
            raise FileNotFoundError(f'Path {data[key]} does not exist')

    return data

def showError(title: str, message: str) -> None:
    """
    Shows an error dialog with the given title and message

    :param title: The title of the error dialog
    :param message: The message displayed in the error dialog
    """
    error_dialog = QErrorMessage()
    error_dialog.setWindowTitle(title if title else 'Error')
    error_dialog.showMessage(message)
    error_dialog.exec()

def svgToQImage(svg_path:str, image_size: QSize) -> QImage:
    """
    Converts the given svg to a QImage with the given size

    :param svg_path: The path to the svg file
    :param image_size: The size of the resulting image
    :return: The resulting QImage
    """
    renderer = QSvgRenderer(svg_path)

    # Create a transparent image
    image = QImage(image_size, QImage.Format.Format_ARGB32)
    image.fill(0x00000000)

    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    renderer.render(painter)
    painter.end()

    return image

def copyFile(source: str, destination: str, force: bool=True) -> None:
    """
    Copy a file from source to destination
    
    :param source: The path to the file that should be copied
    :param destination: The path to where to file should be copied to
    :param force: Whether an existing file should be overwritten
    """
    if os.path.exists(destination):
        if force:
            os.remove(destination)
        else:
            raise FileExistsError(f'File {destination} already exists')

    shutil.copy(source, destination)

def default_preprocessing(input_file: str, image_dir: str, output_file: str):
    """
    This function is used to preprocess the metadata file.
    It only applies preprocessing for metadata files that have a column called "Obj_ Id_" and no "encoding_id" column.
    Otherwise, it just copies the file

    :param input_file: The input file, either xls or csv
    :param image_dir: The directory where the images are stored
    :param output_file: The path where the output file should be stored
    """
    # Read the input file
    file_type = input_file.split(".")[-1]

    if file_type == "csv":
        df = pd.read_csv(input_file, dtype=str)
    elif file_type == "xlsx":
        df = pd.read_excel(input_file, dtype=str)
    else:
        raise ValueError(f"File type {file_type} not supported")

    # Check if the file contains the necessary columns
    if not "Obj_ Id_" in df.columns or "encoding_id" in df.columns:
        df.to_csv(output_file, index=False)
        return

    # Add the encoding_id column
    df["encoding_id"] = -1
    dataset = ImageDataset(image_dir, None)

    # Iterate over all rows and add the encoding_id if possible
    for i in range(len(dataset)):
        # Adjust path to use "/" as separator (otherwise it won't work on Windows)
        path = dataset.image_paths[i]
        path = path.replace("\\", "/")
        
        # Get the filename without extension
        file_name = path.split("/")[-1].split(".")[0]

        try:
            frame = df[df["Obj_ Id_"] == file_name]
        except:
            continue
        if not frame.empty:
            df.at[frame.index[0], "encoding_id"] = i

    # Save the file
    df.to_csv(output_file, index=False)
