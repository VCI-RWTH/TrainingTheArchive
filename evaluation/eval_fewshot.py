from DataLoader import FewShotDataset, MiniImageNetDataLoader
import sys
from argparse import ArgumentParser

import torch
import torch.nn as nn
import torch.nn.functional as fn
# from pcl_toolbox.trainer import Logger, _sanitize_loss_dict
from torch.utils.data import DataLoader
from tqdm import tqdm

sys.path.insert(0, '..')

from models import load_model, load_tokenize
import Embedding
import Coop


def optimize_embedding(images, labels, device):
    group_embeddings = []
    pos_example = []
    neg_example = []
    with torch.no_grad():
        img_encodings = embedder.encode_image(images)
        for i in range(len(labels)):
            num_shots = len(labels[i])
            pos_example.append(img_encodings[num_shots * i: num_shots * (i + 1)])
            neg_example.append(torch.cat([img_encodings[:num_shots * i], img_encodings[num_shots * (i + 1):]]))
            group_embeddings.append(tokenize(labels[i][0]).to(device))
        embedder.update_data(group_embeddings, pos_example, neg_example)

    for i in range(500):
        embedder.optimize_embedding(group_embeddings, pos_example, neg_example)


def evaluate_baseline(images, labels, device):
    img_encodings = embedder.encode_image(images)
    text_encodings = []
    num_ways = len(labels)
    num_shots = len(labels[0])
    for i in range(len(labels)):
        token = tokenize(labels[i][0]).to(device)
        text_encodings.append(fn.normalize(embedder.encode_text(token), dim=-1)[0])
    text_encodings = torch.stack(text_encodings)
    similarity = img_encodings @ text_encodings.T

    indices = similarity.argmax(dim=1)
    truth = torch.cat([torch.ones(num_shots, device=device) * i for i in range(num_ways)])

    return (indices == truth).sum() / truth.shape[0]


def evaluate_embedding(images, labels, device):
    text_encodings = []
    num_ways = len(labels)
    num_shots = len(labels[0])
    with torch.no_grad():
        img_encodings = embedder.embed_image(images)
        for i in range(len(labels)):
            token = tokenize(labels[i][0]).to(device)
            text_encodings.append(fn.normalize(embedder.embed_text(token), dim=-1)[0])
        text_encodings = torch.stack(text_encodings)
        similarity = img_encodings @ text_encodings.T

        indices = similarity.argmax(dim=1)
        truth = torch.cat([torch.ones(num_shots, device=device) * i for i in range(num_ways)])

    return (indices == truth).sum() / truth.shape[0]


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("--name", type=str)
    parser.add_argument("--dataset", type=str)
    parser.add_argument("--n-episodes", type=int, default=60)
    parser.add_argument("--n-shots", type=int, default=10)
    parser.add_argument("--n-way", type=int, default=10)
    parser.add_argument("--n-test", type=int, default=10)
    parser.add_argument("--lr", type=float, default=1e-4)
    args = parser.parse_args()

    print(args)

    args.device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')
    args.device = torch.device('cpu')
    model, preprocess = load_model(args.name, args.device)
    tokenize = load_tokenize(args.name)

    if args.dataset == 'META':
        dataset = FewShotDataset(args.n_shots, args.n_way, args.n_test, transform=preprocess)
        dataset.create_meta_sets('/clusterarchive/MET_data/imagesSmall/',
                                 '/clusterstorage/mibing/datasets/MET_meta/images_map.csv', 'Country', 60,
                                 args.n_episodes)
    elif args.dataset == 'ARTigo':
        dataset = FewShotDataset(args.n_shots, args.n_way, args.n_test, transform=preprocess)
        dataset.create_artigo_sets("/clusterarchive/ARTigo/images/", "/clusterarchive/ARTigo/resource.csv",
                                   "/clusterarchive/ARTigo/tag.csv", "/clusterarchive/ARTigo/tagging.csv", 100,
                                   args.n_episodes)
    elif args.dataset == 'wikiart':
        dataset = FewShotDataset(args.n_shots, args.n_way, args.n_test, transform=preprocess)
        dataset.create_wikiart_sets("/clusterarchive/mibing/datasets/wikiart/", 22, args.n_episodes)
    elif args.dataset == 'ImageNet':
        dataset = MiniImageNetDataLoader(args.n_shots, args.n_way, args.n_test, transform=preprocess)
        dataset.generate_data_list(phase='train')
        dataset.load_list(phase='train')
    else:
        print("Invalid Dataset")

    loss_func = Embedding.CenterMarginLoss(0.1)

    # logger = Logger(args.run_name, log_tensorboard=True, checkpoint_frequency=100,
    #                 logs_folder='../logs', models_folder='../checkpoints')

    pbar = tqdm(range(args.n_episodes))
    trained_acc = 0
    embedding_acc = 0
    degrading_acc = 0
    baseline_acc = 0
    degrading_baseline_acc = 0
    for episode in pbar:
        # refiner = Embedding.LocalMLP(512).to(args.device)
        # embedder = Embedding.LocalLinearEmbedding(512, 10).to(args.device)
        # embedder = Embedding.Embedder(model, refiner)
        embedder = Coop.CustomCLIP(model)

        shot_img, shot_lbl, test_img, test_lbl = dataset.get_batch(idx=episode)
        _, _, test_img2, test_lbl2 = dataset.get_batch(idx=(episode + 1) % args.n_episodes)
        shot_img, test_img, test_img2 = shot_img.to(args.device), test_img.to(args.device), test_img2.to(args.device)
        optimize_embedding(shot_img, shot_lbl, args.device)
        accuracy = evaluate_embedding(shot_img, shot_lbl, args.device)
        trained_acc += accuracy
        # print(accuracy)
        accuracy = evaluate_embedding(test_img, test_lbl, args.device)
        # print(accuracy)
        embedding_acc += accuracy
        accuracy = evaluate_embedding(test_img2, test_lbl2, args.device)
        # print(accuracy)
        degrading_acc += accuracy
        accuracy = evaluate_baseline(test_img, test_lbl, args.device)
        # print(accuracy)
        baseline_acc += accuracy
        accuracy = evaluate_baseline(test_img2, test_lbl2, args.device)
        # print(accuracy)
        degrading_baseline_acc += accuracy

    print("trained: ", trained_acc / args.n_episodes)
    print("embedding: ", embedding_acc / args.n_episodes)
    print("embedding next: ", degrading_acc / args.n_episodes)
    print("baseline: ", baseline_acc / args.n_episodes)
    print("baseline next: ", degrading_baseline_acc / args.n_episodes)
