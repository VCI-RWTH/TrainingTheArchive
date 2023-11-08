import torch

from models import ArtAE, ARTigoEncoder, preprocess_ae, preprocess_artigo


def load_model(model_name, device):
    if model_name == "CLIP":
        import clip
        return clip.load("ViT-B/32", device=device, jit=False)
    if model_name == "OpenCLIP":
        import open_clip
        model, _, preprocess = open_clip.create_model_and_transforms('ViT-B-32-quickgelu',
                                                                     pretrained='laion400m_e32', device=device)
        return model, preprocess
    elif model_name == "AE":
        ae = ArtAE(1024)
        path = '/data/hdd-storage1/lim/art_annotation/met_data/final_art_autoencoder/100epoch_complete_art_autoencoder_1024embed.pt'
        ae.load_state_dict(torch.load(path))
        ae.to(device).eval()
        return ae, preprocess_ae
    elif model_name == "ARTigo":
        model = ARTigoEncoder()
        path = "/home/mibing/Projects/Triplet-Embedding-NN/model_state/artigo_4losses"
        model.load_state_dict(torch.load(path))
        model.to(device).eval()
        return model, preprocess_artigo
    else:
        print("ERROR: " + model_name + " does not exist")


def load_tokenize(model_name):
    if model_name == "CLIP":
        import clip
        return clip.tokenize
    if model_name == "OpenCLIP":
        import open_clip
        return open_clip.get_tokenizer('ViT-B-32-quickgelu')
    elif model_name == "AE":
        return None
    elif model_name == "ARTigo":
        return lambda a: a.split(" ")
    else:
        print("ERROR: " + model_name + " does not exist")
