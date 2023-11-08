import math
import os.path
import sys
from argparse import ArgumentParser

import h5py
import numpy as np
import torch
import torch.nn.functional as fn
from PIL import Image as PIL_Image
from torch.utils.data import DataLoader
from tqdm import tqdm

sys.path.insert(0, '..')

from data import ImageDataset
from models import load_model

def generate_dataset(image_dir, output_dir, batch_size=100, output_name='MET', name='CLIP', thread=None):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model, preprocess = load_model(name, device)

    dataset = ImageDataset(image_dir, preprocess)
    data_loader = DataLoader(dataset, batch_size=batch_size, shuffle=False)

    # This is used to update the progress bar in the GUI
    # Thread is None if the script is called from the command line
    if thread:
        thread.starting.emit(len(dataset))
        value = 0

    image_features = []
    for images in tqdm(data_loader):

        if thread:
            value += len(images)
            thread.valueChanged.emit(value)

        images = images.to(device)
        with torch.no_grad():
            features = model.encode_image(images)
            features = fn.normalize(features, dim=-1)
            image_features.append(features.cpu().numpy())
    image_features = np.concatenate(image_features)

    with h5py.File(output_dir + output_name + "_" + name + ".hdf5", 'w') as master_file:
        encoding = master_file.create_dataset('encoding', image_features.shape, dtype=float)
        encoding[:] = image_features

    if not os.path.isfile(output_dir + output_name + "_info.hdf5"):
        image_width = np.empty(len(dataset))
        for i, path in enumerate(dataset.image_paths):
            image = PIL_Image.open(path)
            image_size = image.size
            image_width[i] = math.ceil(image_size[0] * (100 / image_size[1]))

        with h5py.File(output_dir + output_name + "_info.hdf5", 'w') as master_file:
            string_type = h5py.special_dtype(vlen=str)
            path = master_file.create_dataset('path', (len(dataset),), dtype=string_type)
            path[:] = dataset.image_paths
            widths = master_file.create_dataset('image_width', (len(dataset),), dtype=int)
            widths[:] = image_width

    if thread:
        thread.finished.emit(True)

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("--name", type=str, default='CLIP')
    parser.add_argument("--image-dir", type=str, default='/clusterarchive/MET_data/imagesSmall/')
    parser.add_argument("--output-dir", type=str, default='/clusterarchive/mibing/datasets/LuFo/')
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument("--output-name", type=str, default='MET')
    args = parser.parse_args()

    generate_dataset(args.image_dir, args.output_dir, args.batch_size, args.output_name, args.name)