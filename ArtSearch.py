import sys
import os
import ctypes
import time
from threading import Thread

import h5py
import pandas as pd
import torch
import json
from PIL import Image

from SearchEngine import SearchEngine, METASearch
from Translation import Translator


def load_encodings(path):
    with h5py.File(path, 'r') as master_file:
        encodings = torch.from_numpy(master_file['encoding'][:]).float()
        return encodings


def load_paths(path):
    with h5py.File(path, 'r') as master_file:
        paths = master_file['path'][:]
        return paths


def load_widths(path):
    with h5py.File(path, 'r') as master_file:
        widths = master_file['image_width'][:]
        return widths


def thread(function):
    t1 = Thread(target=function)
    t1.setDaemon(True)
    t1.start()


class ArtSearch:
    def __init__(self, paths_path, encodings_path, meta_path):
        # path to the hdf5 file, that saves all image paths should have ending _paths.hdf5
        self.paths_path = paths_path
        # path to the hdf5 file, that saves all image embeddings.
        # The ending should correspond to the model used for search e.g. CLIP
        self.encodings_path = encodings_path
        # path to the csv containing the meda_data for the images.
        # The csv needs to have a column "encoding_id"
        # corresponding to the position of the image in the previous two arrays
        self.meta_path = meta_path

        self.init_search_engines()
        self.translator = Translator("DE")

        # arrays that tell us for the canvas and each group whether each image is inside or outside
        # an image that has not been processed is neither inside nor outside,
        # as it should not take part in the optimization
        self.positive = torch.zeros(1, (len(self.paths)), dtype=torch.bool)
        self.negative = torch.zeros(1, (len(self.paths)), dtype=torch.bool)

        self.last_search_term = ''
        self.groups = []
        self.scene = None
        self.lang = 'EN'
        thread(self.update_latent)

    def init_search_engines(self):
        self.paths = load_paths(self.paths_path)
        self.image_widths = load_widths(self.paths_path)

        self.search_engines = {}
        self.search_engines['CLIP'] = SearchEngine("CLIP", load_encodings(self.encodings_path))
        # self.search_engines['CLIP'] = SearchEngine("OpenCLIP", load_encodings(self.encodings_path))

        # for each metadata entry we add a search engine
        df = pd.read_csv(self.meta_path, delimiter=',', dtype='str')
        for key in df.keys():
            if key != 'encoding_id':
                self.search_engines[key] = METASearch(key, df)

    def content_change(self):
        for key, search in self.search_engines.items():
            if isinstance(search, SearchEngine):
                search.data_changed = True

    def restrict_search(self, filters):
        search_results = []
        for key, value in filters:
            if value != "":
                # collect ids of all images that fulfill the restriction
                search_results.append(self.search_engines[key].search_by_text(None, value, None).tolist())

        # Remove empty lists (happens when no results were found for the given value)
        search_results = [result for result in search_results if result]

        if search_results:
            # only ids, that fulfill all constraints are valid
            constraints = torch.tensor(list(set.intersection(*map(set, search_results))))
            valid = torch.zeros_like(self.positive[0])
            valid[constraints] = True
            valid = torch.logical_and(~self.positive[0], valid)
            valid = torch.logical_and(~self.negative[0], valid)
        else:
            valid = torch.logical_and(~self.positive[0], ~self.negative[0])

        return valid

    def text_search(self, search_text, filters):
        self.last_search_term = search_text
        valid = self.restrict_search(filters)
        if self.lang == 'DE':
            search_text = self.translator.translate(search_text)
            print(search_text)

        return self.search_engines["CLIP"].search_by_text(valid, search_text, len(self.paths)).tolist()

    def image_search(self, image, filters):
        valid = self.restrict_search(filters)
        return self.search_engines["CLIP"].search_by_image(valid, Image.open(image), len(self.paths)).tolist()

    def remove_group(self, group):
        # Offset the index by one because the first entry is the canvas
        index = self.groups.index(group) + 1
        self.groups.remove(group)

        def delete(arr: torch.Tensor, ind: int, dim: int) -> torch.Tensor:
            skip = [i for i in range(arr.shape[dim]) if i != ind]
            indices = [slice(None) if i != dim else skip for i in range(arr.ndim)]
            return arr.__getitem__(indices)

        self.positive = delete(self.positive, index, 0)
        self.negative = delete(self.negative, index, 0)

    def create_group(self, group):
        self.groups.append(group)
        if len(self.groups) >= len(self.positive):
            self.positive = torch.cat([self.positive, torch.zeros_like(self.positive[:1])], dim=0)
            self.negative = torch.cat([self.negative, self.negative[:1].clone()], dim=0)

    # this function continuously updates the latent space /embedding tensor
    def update_latent(self):
        # Using torch 2.1.0 will cause this function to crash
        steps = 0
        while True:
            steps += 1
            for key, search in self.search_engines.items():
                if isinstance(search, SearchEngine) and search.data_changed:
                    group_names = [group.getName() for group in self.groups]
                    search.update_group_embeddings(self.positive[:len(self.groups) + 1],
                                                   self.negative[:len(self.groups) + 1],
                                                   group_names)
                if isinstance(search, SearchEngine):
                    search.optimize_embedding()
                    search.update_embedding()  # This does not need to be done this often
                time.sleep(0.001)

            if steps == 1000:  # no practical use, just to see something happening
                print("update embedding")
                steps = 0

    def update(self):
        for key, search in self.search_engines.items():
            if isinstance(search, SearchEngine):
                group_names = [group.getName() for group in self.groups]
                search.update_group_embeddings(self.positive[:len(self.groups) + 1],
                                               self.negative[:len(self.groups) + 1],
                                               group_names)
            if isinstance(search, SearchEngine):
                search.optimize_embedding()
                search.update_embedding()

    def updateGroup(self, group, positive, negative) -> None:
        index = self.groups.index(group)

        self.positive[index + 1] = torch.zeros_like(self.positive[index])
        self.positive[index + 1][positive] = True

        self.negative[index + 1] = torch.zeros_like(self.negative[index])
        self.negative[index + 1][negative] = True

    def setImageNeutral(self, image_id: int) -> None:
        self.positive[0][image_id] = False
        self.negative[0][image_id] = False

    def setImageNegative(self, image_id: int) -> None:
        self.positive[0][image_id] = False
        self.negative[0][image_id] = True

    def setImagePositive(self, image_id: int) -> None:
        self.positive[0][image_id] = True
        self.negative[0][image_id] = False

    def getImagePath(self, image_id: int) -> str:
        path = str(self.paths[image_id]).replace("\\\\", "/")[2:-1]

        # Repalce relative paths
        if not os.path.isabs(path):
            path = os.path.join(os.path.dirname(__file__), path)

        return path
    
    def reset(self) -> None:
        self.positive = torch.zeros(1, (len(self.paths)), dtype=torch.bool)
        self.negative = torch.zeros(1, (len(self.paths)), dtype=torch.bool)

    def serialize(self) -> dict:
        return {
            'positive': self.positive[0].nonzero().flatten().tolist(),
            'negative': self.negative[0].nonzero().flatten().tolist(),
        }

    def deserialize(self, data) -> None:
        self.groups = []

        self.positive = torch.zeros(1, (len(self.paths)), dtype=torch.bool)
        self.negative = torch.zeros(1, (len(self.paths)), dtype=torch.bool)

        for index in data['positive']:
            self.positive[0][index] = True
        for index in data['negative']:
            self.negative[0][index] = True
