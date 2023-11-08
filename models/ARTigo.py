import torch.nn as nn
import torch
import torch.nn.functional as fn
import random
import torchvision
import torchvision.transforms as transforms


def get_multy_tag_indexes(tags):
    indexes = []
    for tag in tags:
        indexes.append(torch.nonzero(tag).view(-1).tolist())
    return indexes


def get_index_matrix(tag_matrix, padding_index, max_length, padding_mask=False, eos=False, device=torch.device('cpu')):
    if max_length == -1:
        max_length = max(int(torch.max(torch.sum(tag_matrix, dim=-1)).item()), 5)
    length_list = torch.clamp(torch.sum(tag_matrix, dim=-1), max=max_length).long()

    index_matrix = []

    if padding_mask:
        src_key_padding_mask = torch.ones((tag_matrix.shape[0], max_length + int(eos))).to(device)

    all_indeces = get_multy_tag_indexes(tag_matrix)

    for i in range(tag_matrix.shape[0]):
        indeces = all_indeces[i]
        if len(indeces) > max_length:
            indeces = random.sample(indeces, max_length)
        if padding_mask:
            if eos:
                src_key_padding_mask[i][0:len(indeces) + 1] = torch.tensor([0] * (len(indeces) + 1))
            else:
                src_key_padding_mask[i][0:len(indeces)] = torch.tensor([0] * len(indeces))

        indeces.extend([padding_index] * (max_length - len(indeces) + int(eos)))
        index_matrix.append(indeces)

    index_matrix = torch.tensor(index_matrix).to(device)

    if padding_mask:
        return index_matrix, length_list, src_key_padding_mask
    else:
        return index_matrix, length_list


def get_tag_matrix(tag_name_matrix, tag_list, device=torch.device('cpu')):
    tag_num = len(tag_list)
    tag_matrix = torch.zeros((len(tag_name_matrix), tag_num))
    tag_name_index_dic = dict(zip(tag_list, range(0, tag_num)))
    for i in range(len(tag_name_matrix)):
        for tag in tag_name_matrix[i]:
            tag_matrix[i, tag_name_index_dic[tag]] = 1
    return tag_matrix.to(device)


class TransformerModel(nn.Module):

    def __init__(self, ntag, feature_dim, token_embedding_matrix, dropout=0.5):
        super().__init__()
        self.model_type = 'Transformer'

        # batch_first=True
        nhead = 8  # options.transformer_nhead
        self.d_hid = 512  # options.transformer_d_hid
        # d_model  the number of expected features in the encoder/decoder inputs
        self.token_embedding_dim = token_embedding_matrix.shape[1]
        encoder_layers = nn.TransformerEncoderLayer(self.token_embedding_dim, nhead, self.d_hid, dropout,
                                                    batch_first=True)
        nlayers = 6  # options.transformer_nlayers
        self.transformer_encoder = nn.TransformerEncoder(encoder_layers, nlayers)

        self.ntoken = ntag + 1
        self.feature_dim = feature_dim
        self.max_length = 16  # options.tag_max_length
        self.eos_index = self.ntoken - 1

        self.sentence_feature = "sum"  # options.sentence_feature
        self.fc_layer = True  # options.fc_layer
        if self.sentence_feature == "eos":
            self.token_embedding = nn.Embedding(self.ntoken, self.token_embedding_dim)
            self.token_embedding.weight.data.copy_(token_embedding_matrix)
        else:
            self.token_embedding = nn.Embedding(self.ntoken, self.token_embedding_dim, padding_idx=self.ntoken - 1)
            token_embedding_matrix[-1] = token_embedding_matrix[-1] * 0
            self.token_embedding.weight.data.copy_(token_embedding_matrix)

        if self.fc_layer:
            self.fc = nn.Linear(self.token_embedding_dim, feature_dim)

    def forward(self, tag_matrix):
        """
        Args:
            tag_matrix: Tensor, shape [batch_size, ntoken-1]

        Returns:
            output Tensor of shape [batch_size, feature_dim]
        """
        index_matrix, eos_position, padding_mask = get_index_matrix(tag_matrix, self.eos_index,
                                                                    self.max_length, padding_mask=True,
                                                                    eos=self.sentence_feature == "eos",
                                                                    device=self.fc.weight.device)

        # [batch_size, max_length, token_embedding_dim]
        token_embedding_matrix = self.token_embedding(index_matrix)
        output = self.transformer_encoder(token_embedding_matrix, src_key_padding_mask=padding_mask)
        # print(output.shape)
        if self.sentence_feature == "eos":
            output = torch.stack([output[i, eos_position[i]] for i in range(len(output))])
        elif self.sentence_feature == "sum":
            output = torch.sum(output, dim=-2)
        elif self.sentence_feature == "mean":
            output = torch.mean(output, dim=-2)
        elif self.sentence_feature == "max":
            output = torch.max(output, dim=-2)[0]
        # print(output.shape)
        if self.fc_layer:
            output = self.fc(output)
        return fn.normalize(output)


class ARTigoEncoder(nn.Module):
    def __init__(self):
        super().__init__()

        self.tags = ['akt', 'baum', 'berg', 'blau', 'blätter', 'dunkel', 'feder', 'felsen', 'feuer', 'flügel',
                     'gemälde', 'gott', 'hand', 'himmel', 'kampf', 'kopf', 'laub', 'mann', 'meer', 'nackt', 'schatten',
                     'umhang', 'vogel', 'wasser', 'weiß', 'wolken', 'aquarell', 'bäume', 'fluss', 'frauen', 'gelb',
                     'grün', 'impressionismus', 'landschaft', 'menschen', 'mädchen', 'sand', 'see', 'sitzen', 'stadt',
                     'ufer', 'äste', 'blume', 'blumen', 'braun', 'brust', 'bunt', 'busen', 'fenster', 'finger',
                     'frankreich', 'frau', 'frisur', 'glas', 'grau', 'haar', 'hell', 'holz', 'hut', 'hüte', 'kleid',
                     'kleider', 'licht', 'marmor', 'mund', 'männer', 'nacht', 'nase', 'ohr', 'orange', 'profil', 'raum',
                     'rücken', 'schwarz', 'skizze', 'stirn', 'strasse', 'straße', 'stuhl', 'stühle', 'säule', 'säulen',
                     'tisch', 'tür', 'weiss', 'zeichnung', 'zimmer', 'blick', 'blüten', 'dach', 'dame', 'gebäude',
                     'gras', 'haus', 'hund', 'obst', 'park', 'rot', 'schloss', 'schnee', 'tier', 'tiere', 'tuch', 'weg',
                     'wiese', 'wolke', 'zaun', 'haube', 'muster', 'ornament', 'rock', 'schleife', 'tanz', 'teppich',
                     'zylinder', 'alt', 'anzug', 'bart', 'hemd', 'hose', 'jacke', 'kappe', 'mütze', 'wand',
                     'architektur', 'arm', 'arme', 'augen', 'barock', 'falten', 'federn', 'gesicht', 'kragen', 'mensch',
                     'pelz', 'rahmen', 'schale', 'sockel', 'stein', 'steine', 'teller', 'tod', 'tot', 'bild', 'bildnis',
                     'hals', 'hände', 'portrait', 'porträt', 'signatur', 'spiegel', 'vorhang', 'öl', 'bach', 'feld',
                     'horizont', 'häuser', 'hügel', 'kühe', 'natur', 'spiegelung', 'vögel', 'wind', 'brücke', 'büsche',
                     'hütte', 'kirche', 'rauch', 'sonne', 'boden', 'figur', 'gewand', 'gold', 'haare', 'mantel',
                     'sessel', 'sitzend', 'decke', 'familie', 'kind', 'mutter', 'paar', 'musik', 'pflanzen', 'gotik',
                     'krone', 'lippen', 'locken', 'rosa', 'wald', 'boot', 'boote', 'brunnen', 'esel', 'kamin', 'kinder',
                     'kreis', 'oval', 'pferd', 'pferde', 'reiter', 'rund', 'schornstein', 'stock', 'turm', 'engel',
                     'garten', 'krug', 'skulptur', 'statue', 'stilleben', 'stillleben', 'vase', 'beine', 'perücke',
                     'balkon', 'relief', 'küste', 'schiff', 'schiffe', 'schrift', 'segel', 'strand', 'wellen', 'bilder',
                     'bücher', 'papier', 'liegen', 'bogen', 'fassade', 'italien', 'schuhe', 'stab', 'studie', 'fahne',
                     'abstrakt', 'berge', 'fels', 'gebirge', 'kette', 'dorf', 'dächer', 'giebel', 'mauer', 'grafik',
                     'graphik', 'kuh', 'linien', 'hof', 'winter', 'kutsche', 'platz', 'bank', 'saal', 'figuren',
                     'hafen', 'wagen', 'kuppel', 'krieg', 'schlacht', 'sturm', 'treppe', 'blue', 'hat', 'kissen',
                     'könig', 'men', 'people', 'red', 'soldaten', 'thron', 'white', 'women', 'black', 'dress', 'green',
                     'hair', 'nose', 'painting', 'portrait', 'woman', 'kopftuch', 'inschrift', 'büste', 'uhr', 'bett',
                     'korb', 'stuck', 'brown', 'geländer', 'stufen', 'bronze', 'junge', 'knöpfe', 'tor', 'foto',
                     'fotografie', 'bögen', 'eingang', 'schild', 'ruine', 'gewölbe', 'buch', 'burg', 'kreuz', 'türme',
                     'palast', 'strahlen', 'druck', 'radierung', 'stich', 'seite', 'schwarzweiß', 'schwert', 'text',
                     'uniform', 'soldat', 'bleistift', 'helm', 'beten', 'entwurf', 'kranz', 'ritter', 'rüstung',
                     'altar', 'rom', 'photo', 'portal', 'wappen', 'heiligenschein', 'christus', 'jesus', 'kreuzigung',
                     'clouds', 'man', 'sky', 'tree', 'building', 'house', 'landscape', 'water', 'trees', 'mönch',
                     'eyes', 'plan', 'tempel', 'löwe', 'heilige', 'fresko', 'grass', 'drawing', 'putten', 'maria',
                     'kupferstich', 'turban', 'beard', 'grundriss', 'aufriss', 'latein', 'horse', 'buchmalerei']

        class Wrapper(nn.Module):
            def __init__(self, model):
                super().__init__()
                self.model = model

        self.image_model = Wrapper(torchvision.models.resnet101(pretrained=False))
        self.tag_model = Wrapper(TransformerModel(ntag=len(self.tags), feature_dim=1000,
                                                  token_embedding_matrix=torch.zeros(len(self.tags) + 1, 256),
                                                  dropout=0.5))

    def encode_image(self, x):
        return self.image_model.model(x)

    def encode_text(self, x):
        x = get_tag_matrix([x], self.tags, device=self.tag_model.model.fc.weight.device)
        return self.tag_model.model(x)

    def load_state_dict(self, state_dict: 'OrderedDict[str, Tensor]',
                        strict: bool = True):
        self.image_model.load_state_dict(state_dict['image_model_state_dict'])
        self.tag_model.load_state_dict(state_dict['tag_model_state_dict'])


def preprocess_artigo(image):
    image = image.convert('RGB')
    transform = transforms.Compose([transforms.Resize((224, 224)),
                                    transforms.ToTensor()])
    image = transform(image)
    return image
