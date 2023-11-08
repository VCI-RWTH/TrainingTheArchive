import os

import torch.utils.data
from PIL import Image, ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = True


class ImageDataset(torch.utils.data.Dataset):
    def __init__(self, path, transform):
        self.transform = transform
        self.image_paths = []
        valid_images = [".jpg", ".png", ".tga", ".bmp", ".jpeg", ".gif"]
        for f in os.listdir(path):
            ext = os.path.splitext(f)[1]
            if ext.lower() not in valid_images:
                continue
            self.image_paths.append(os.path.join(path, f))

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        return self.transform(Image.open(self.image_paths[idx]))
