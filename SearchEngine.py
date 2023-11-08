import torch
import torch.nn.functional as fn

import Embedding
from models import load_model, load_tokenize


class SearchEngine:
    def __init__(self, type, encodings):
        self.type = type
        model, self.preprocess = load_model(self.type, "cpu")
        self.tokenize = load_tokenize(self.type)

        # encodings based on the pretrained model used for search e.g. CLIP
        # these are used when focus mode is off
        self.encodings = fn.normalize(encodings, dim=-1)
        # refined embeddings based on the search done so far, used when focus mode is on
        self.embeddings = self.encodings.clone()

        # model that updates embeddings based on group description and assigned images
        embedder = Embedding.LocalSplitMLP(self.encodings.shape[-1])
        # embedder = Embedding.LocalLinearSplitNet(self.encodings.shape[-1], 50, 1e-3, 0.5, True)
        self.embedder = Embedding.Embedder(model, embedder)

        self.group_embeddings = []
        self.pos_example = []
        self.neg_example = []

        # information that somehow the content of the canvas has changed (added or removed image etc.)
        # whenever this happens we reload the entire data for the embedding which is rather wasteful
        self.data_changed = True
        self.use_embedding = True

    def search_by_text(self, valid, text, topk):
        token = self.tokenize(text)
        topk = min(topk, valid.nonzero().shape[0])

        with torch.no_grad():
            if self.use_embedding:
                text_features = self.embedder.embed_text(token)
                similarity = (self.embeddings * valid.unsqueeze(1)) @ text_features.T
            else:
                text_features = self.embedder.encode_text(token)
                similarity = (self.encodings * valid.unsqueeze(1)) @ text_features.T

        values, indices = similarity[:, 0].topk(topk)

        return indices

    def search_by_image(self, valid, image, topk):
        with torch.no_grad():
            image = self.preprocess(image).unsqueeze(0)
            if self.use_embedding:
                image_features = self.embedder.embed_image(image)
                similarity = (self.embeddings * valid.unsqueeze(1)) @ image_features.T
            else:
                image_features = self.embedder.encode_image(image)
                similarity = (self.encodings * valid.unsqueeze(1)) @ image_features.T

        values, indices = similarity[:, 0].topk(topk)

        return indices

    def update_group_embeddings(self, positive, negative, group_names):
        self.pos_example = []
        self.neg_example = []
        self.group_embeddings = []
        for i in range(positive.shape[0]):
            if i == 0:
                continue  # TODO still unsure whether to do anything "global"
                # self.pos_example.append(self.encodings[positive[i]])
                # self.neg_example.append(self.encodings[negative[i]])
                # self.group_embeddings.append([])
            else:
                self.pos_example.append(self.encodings[positive[i]])
                self.neg_example.append(self.encodings[negative[i]])
                self.group_embeddings.append(self.tokenize(group_names[i - 1]))

        self.embedder.update_data(self.group_embeddings, self.pos_example, self.neg_example)
        self.data_changed = False

    def optimize_embedding(self):
        self.embedder.optimize_embedding(self.group_embeddings, self.pos_example, self.neg_example)

    def update_embedding(self):
        self.embeddings = self.embedder.refine_image_embedding(self.encodings)[0]


class METASearch:
    def __init__(self, type, table):
        self.type = type
        self.table = table

    def search_by_text(self, valid, key, topk):
        indices = torch.tensor(self.table[self.table[self.type] == key]["encoding_id"].astype(int).tolist())
        indices = indices[indices != -1]

        return indices

    def search_by_id(self, idx):
        info = self.table[self.table["encoding_id"] == str(idx)]
        if not info.empty:
            info = info.iloc[0][self.type]
            if not isinstance(info, str):
                info = str(info)
            return info
        else:
            return None
