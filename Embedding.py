import torch
import torch.nn as nn
import torch.nn.functional as fn
from sklearn.cluster import AgglomerativeClustering


class DiagonalEmbedding(nn.Module):
    def __init__(self, dim):
        super(self.__class__, self).__init__()

        self.weights = nn.Parameter(torch.ones(dim))

    def forward(self, inp):
        return fn.normalize(inp * self.weights, dim=-1)


class LinearEmbedding(nn.Module):
    def __init__(self, dim):
        super(self.__class__, self).__init__()

        self.weights = nn.Parameter(torch.eye(dim))

    def forward(self, inp):
        return fn.normalize(inp @ self.weights, dim=-1)


class LocalLinearEmbedding(nn.Module):
    def __init__(self, dim, cluster):
        super(self.__class__, self).__init__()

        self.value = nn.ModuleList([])
        for i in range(cluster):
            if i == 0:
                self.value.append(nn.Linear(dim, dim))
                self.value[-1].weight = nn.Parameter(torch.eye(dim), requires_grad=False)
                self.value[-1].bias = nn.Parameter(torch.zeros(dim), requires_grad=False)
            else:
                self.value.append(nn.Linear(dim, dim))
                self.value[-1].weight = nn.Parameter(torch.eye(dim), requires_grad=True)
                self.value[-1].bias = nn.Parameter(torch.zeros(dim), requires_grad=True)

        self.key = nn.Linear(dim, cluster)
        self.key.bias = nn.Parameter(torch.zeros(cluster))
        self.key.bias.data[0] = 10

    def add_center(self, pos):
        # do nothing
        return

    def regularization(self, keys):
        offset_reg = torch.pow(keys, 2).sum()
        return offset_reg

    def forward(self, inp):
        key = fn.softmax(self.key(inp), dim=1)
        out = 0
        for i, val in enumerate(self.value):
            out += val(inp) * key[:, i].unsqueeze(1)
        return fn.normalize(out, dim=-1), self.regularization(key)

    def encode_text(self, inp):
        return self.forward(inp)

    def encode_image(self, inp):
        return self.forward(inp)


class RBFCluster(nn.Module):
    def __init__(self, dim, cluster):
        super(self.__class__, self).__init__()

        self.n_cluster = cluster
        self.offset = nn.Parameter(torch.zeros(cluster, dim))
        self.pos = nn.Parameter(torch.randn(cluster, dim))

    def add_center(self, pos):
        # do nothing
        return

    def regularization(self):
        offset_reg = torch.pow(self.offset, 2).sum()
        return offset_reg

    def positional_regularization(self, embeddings):
        return (1 - torch.cosine_similarity(embeddings, self.pos)).mean()

    def forward(self, inp):
        a = fn.normalize(inp)
        b = fn.normalize(self.pos)
        dist = 1 - torch.mm(a, b.transpose(0, 1))
        dist = torch.exp(-(10 * dist))
        out = inp.clone()
        for i in range(self.n_cluster):
            out += self.offset[i, None] * dist[:, i, None]
        return fn.normalize(out, dim=-1), self.regularization()

    def encode_text(self, inp):
        return self.forward(inp)

    def encode_image(self, inp):
        return self.forward(inp)


class LocalMLP(nn.Module):
    def __init__(self, dim):
        super(self.__class__, self).__init__()

        self.mlp = nn.Sequential(
            nn.Linear(dim, dim),
            # nn.ReLU(),
            # nn.Linear(dim, dim),
            # nn.ReLU(),
            # nn.Linear(dim, dim),
        )
        self.mlp[-1].weight = nn.Parameter(torch.eye(dim), requires_grad=True)
        self.mlp[-1].bias = nn.Parameter(torch.zeros(dim), requires_grad=True)
        self.center = []

    def add_center(self, pos):
        self.center.append(pos)

    def regularization(self):
        return (fn.mse_loss(self.mlp[-1].weight,
                            torch.eye(self.mlp[-1].weight.shape[-1], device=self.mlp[-1].weight.device)) +
                fn.mse_loss(self.mlp[-1].bias,
                            torch.zeros(self.mlp[-1].weight.shape[-1], device=self.mlp[-1].weight.device))).mean() * 1e4

    def weight(self, inp):
        a = fn.normalize(inp)
        if len(self.center) > 0:
            b = fn.normalize(torch.cat(self.center))
            dist = 1 - torch.mm(a, b.transpose(0, 1))
            weight = torch.exp(-10 * dist).max()
        else:
            weight = torch.zeros(1)
        weight = weight.detach()
        return weight

    def encode_text(self, inp):
        weight = self.weight(inp)
        out = inp.clone()
        out = fn.normalize(self.mlp(out))
        out = weight * out + (1 - weight) * inp.detach()

        return fn.normalize(out, dim=-1), self.regularization()

    def encode_image(self, inp):
        weight = self.weight(inp)
        out = inp.clone()
        out = fn.normalize(self.mlp(out))
        out = weight * out + (1 - weight) * inp.detach()

        return fn.normalize(out, dim=-1), self.regularization()

    def randomize(self):
        self.mlp[-1].weight.data += torch.randn_like(self.mlp[-1].weight)
        self.mlp[-1].bias.data += torch.randn_like(self.mlp[-1].bias)


class LocalSplitMLP(nn.Module):
    def __init__(self, dim):
        super(self.__class__, self).__init__()

        self.center = []
        self.mlp_image = nn.Sequential(
            nn.Linear(dim, dim),
            # nn.ReLU(),
            # nn.Linear(dim, dim),
            # nn.ReLU(),
            # nn.Linear(dim, dim),
        )
        self.mlp_image[-1].weight = nn.Parameter(torch.eye(dim), requires_grad=True)
        self.mlp_image[-1].bias = nn.Parameter(torch.zeros(dim), requires_grad=True)

        self.mlp_text = nn.Sequential(
            nn.Linear(dim, dim),
            # nn.ReLU(),
            # nn.Linear(dim, dim),
            # nn.ReLU(),
            # nn.Linear(dim, dim),
        )
        self.mlp_text[-1].weight = nn.Parameter(torch.eye(dim), requires_grad=True)
        self.mlp_text[-1].bias = nn.Parameter(torch.zeros(dim), requires_grad=True)

    def regularization(self):
        return (fn.mse_loss(self.mlp_image[-1].weight,
                            torch.eye(self.mlp_image[-1].weight.shape[-1], device=self.mlp_image[-1].weight.device)) +
                fn.mse_loss(self.mlp_image[-1].bias,
                            torch.zeros(self.mlp_image[-1].weight.shape[-1], device=self.mlp_image[-1].weight.device)) +
                fn.mse_loss(self.mlp_text[-1].weight,
                            torch.eye(self.mlp_text[-1].weight.shape[-1], device=self.mlp_text[-1].weight.device)) +
                fn.mse_loss(self.mlp_text[-1].bias,
                            torch.zeros(self.mlp_text[-1].weight.shape[-1],
                                        device=self.mlp_text[-1].weight.device))).mean() * 1e4

    def weight(self, inp):
        a = fn.normalize(inp)
        if len(self.center) > 0:
            b = fn.normalize(torch.cat(self.center))
            dist = 1 - torch.mm(a, b.transpose(0, 1))
            weight = torch.exp(-10 * dist).max()
        else:
            weight = torch.zeros(1)
        weight = weight.detach()
        return weight

    def encode_text(self, inp):
        weight = self.weight(inp)
        out = inp.clone()
        out = fn.normalize(self.mlp_image(out))
        out = weight * out + (1 - weight) * inp.detach()

        return fn.normalize(out, dim=-1), self.regularization()

    def encode_image(self, inp):
        weight = self.weight(inp)
        out = inp.clone()
        out = fn.normalize(self.mlp_text(out))
        out = weight * out + (1 - weight) * inp.detach()

        return fn.normalize(out, dim=-1), self.regularization()


# model used in paper. This however seems to lead to worse results than LocalSplitMLP
class LocalLinearSplitNet(nn.Module):
    def __init__(self, dim, num_clusters, rbf_weight, global_dampening, identity_init):
        super(self.__class__, self).__init__()

        self.linear_text = nn.Linear(dim, dim)
        self.linear_image = nn.Linear(dim, dim)
        if identity_init:
            self.linear_text.weight = nn.Parameter(torch.eye(dim), requires_grad=True)
            self.linear_text.bias = nn.Parameter(torch.zeros(dim), requires_grad=True)
            self.linear_image.weight = nn.Parameter(torch.eye(dim), requires_grad=True)
            self.linear_image.bias = nn.Parameter(torch.zeros(dim), requires_grad=True)
        self.center_list_text = []
        self.center_list_image = []
        self.max_center = num_clusters
        self.rbf_weight = rbf_weight
        if global_dampening < 0:
            self.global_dampening = nn.Parameter(torch.ones(1) * 0.5)
        else:
            self.global_dampening = global_dampening
        self.register_buffer("center_text", torch.empty(0))
        self.register_buffer("center_image", torch.empty(0))

    def add_sample_points_text(self, pos):
        self.center_list_text.append(pos)

    def add_sample_points_image(self, pos):
        self.center_list_image.append(pos)

    def compute_center(self, domain="both"):
        if domain == 'text':
            if len(self.center_list_text) == 0:
                return
            center = fn.normalize(torch.cat(self.center_list_text))
        elif domain == 'image':
            if len(self.center_list_text) == 0:
                return
            center = fn.normalize(torch.cat(self.center_list_image))
        else:
            center = fn.normalize(torch.cat(self.center_list_text + self.center_list_image))
        if -1 < self.max_center < center.shape[0]:
            device = center.device
            clustering = AgglomerativeClustering(n_clusters=self.max_center, affinity='cosine',
                                                 linkage='complete').fit(center.cpu())
            res = torch.zeros(self.max_center, center.shape[1])
            res.index_add_(0, torch.from_numpy(clustering.labels_), center.cpu())
            center = fn.normalize(res, dim=1).to(device)
        if domain == 'text':
            self.center_text = center
        elif domain == 'image':
            self.center_image = center
        else:
            self.center_text = center
            self.center_image = center

    def regularization(self):
        return (fn.mse_loss(self.linear_text.weight,
                            torch.eye(self.linear_text.weight.shape[-1],
                                      device=self.linear_text.weight.device)) +
                fn.mse_loss(self.linear_text.bias,
                            torch.zeros(self.linear_text.weight.shape[-1],
                                        device=self.linear_text.weight.device)) +
                fn.mse_loss(self.linear_image.weight,
                            torch.eye(self.linear_image.weight.shape[-1],
                                      device=self.linear_image.weight.device)) +
                fn.mse_loss(self.linear_image.bias,
                            torch.zeros(self.linear_image.weight.shape[-1],
                                        device=self.linear_image.weight.device))).mean()

    def weight_text(self, inp):
        if self.center_text.shape[0] == 0:
            return torch.zeros(1)

        a = fn.normalize(inp)
        dist = 1 - torch.mm(a, self.center_text.transpose(0, 1)).max().detach().clamp(0, 1)

        if self.rbf_weight < -1000:  # dirac case
            if self.training:
                weight = torch.ones(1).to(inp.device)
            else:
                weight = 1 - (dist + 0.499).round().clamp(0, 1)
        else:
            weight = torch.exp(self.rbf_weight * dist)  # .max().detach()
        return weight * self.global_dampening

    def weight_image(self, inp):
        if self.center_image.shape[0] == 0:
            return torch.zeros(1)

        a = fn.normalize(inp)
        dist = 1 - torch.mm(a, self.center_image.transpose(0, 1)).max().detach().clamp(0, 1)
        if self.rbf_weight < -1000:  # dirac case
            if self.training:
                weight = torch.ones(1).to(inp.device)  # due to data augmentation we would not train otherwise
            else:
                weight = 1 - (dist + 0.499).round().clamp(0, 1)
        else:
            weight = torch.exp(self.rbf_weight * dist)  # .max().detach()
        return weight * self.global_dampening

    def encode_text(self, inp):
        out = inp.clone()
        out = fn.normalize(self.linear_text(out))
        weight = self.weight_text(inp)
        out = weight * out + (1 - weight) * inp.detach()
        return fn.normalize(out, dim=-1), self.regularization()

    def encode_image(self, inp):
        out = inp.clone()
        out = fn.normalize(self.linear_image(out))
        weight = self.weight_image(inp)
        out = weight * out + (1 - weight) * inp.detach()
        return fn.normalize(out, dim=-1), self.regularization()


# wrapper class that contain both the pretrained model and our refiner
# encoding: tex/image to pretrained latent vector
# embedding: tex/image to refined latent vector
# refine: pretrained latent vector to refined latent vector
# also deals with the training of our refinement model
class Embedder(nn.Module):
    def __init__(self, encoder, embedder):
        super(self.__class__, self).__init__()

        self.encoder = encoder
        self.embedder = embedder
        self.loss_func = CenterMarginLoss(0.1)
        self.optimizer = torch.optim.Adam(self.embedder.parameters(), lr=1e-3, amsgrad=True, weight_decay=0)

    def encode_text(self, text):
        text_features = self.encoder.encode_text(text).float()
        text_features = fn.normalize(text_features, dim=-1)
        return text_features

    def embed_text(self, text):
        text_features = self.encode_text(text).float()
        text_features = self.embedder.encode_text(text_features)[0]
        return text_features

    def encode_image(self, image):
        image_features = self.encoder.encode_image(image).float()
        image_features = fn.normalize(image_features, dim=-1)
        return image_features

    def embed_image(self, image):
        image_features = self.encode_image(image).float()
        image_features = self.embedder.encode_image(image_features)[0]
        return image_features

    def refine_image_embedding(self, embedding):
        return self.embedder.encode_image(embedding)

    def refine_text_embedding(self, embedding):
        return self.embedder.encode_text(embedding)

    def update_data(self, group_embeddings, pos_example, neg_example):
        center = []
        for i in range(len(group_embeddings)):
            center.append(pos_example[i])
            center.append(fn.normalize(self.encode_text(group_embeddings[i]), dim=-1).detach())
        self.embedder.center = center

    # def update_data(self, group_embeddings, pos_example, neg_example):
    #     self.embedder.center_list_text = []
    #     self.embedder.center_list_image = []
    #     for i in range(len(group_embeddings)):
    #         self.embedder.add_sample_points_image(pos_example[i])
    #         self.embedder.add_sample_points_text(self.encode_text(group_embeddings[i]).detach())
    #
    #     self.embedder.compute_center("image")
    #     self.embedder.compute_center("text")

    def optimize_embedding(self, group_embeddings, pos_example, neg_example):
        for j in range(len(group_embeddings)):
            if pos_example[j].shape[0] == 0 or neg_example[j].shape[0] == 0:
                continue
            self.optimizer.zero_grad()
            embedding_pos, _ = self.refine_image_embedding(pos_example[j])
            embedding_neg, _ = self.refine_image_embedding(neg_example[j])
            embedding_center, reg = self.refine_text_embedding(
                fn.normalize(self.encode_text(group_embeddings[j]), dim=-1).detach())
            margin_loss = self.loss_func(embedding_center[0], embedding_pos, embedding_neg).sum()
            # dist_loss = self.embedder.positional_regularization(group_embeddings[j])
            loss = margin_loss + reg  # + dist_loss

            loss.backward()
            self.optimizer.step()


class GlobalMarginLoss(nn.Module):
    def __init__(self, margin):
        super(self.__class__, self).__init__()

        self.margin = margin

    def forward(self, feature, label):
        dists = 1.0 - feature @ feature.transpose(0, 1)
        label = label * 2 - 1
        similarity = label.unsqueeze(0) * label.unsqueeze(1)
        similarity = (similarity + 1) / 2

        ind_intra = similarity.nonzero()
        ind_inter = (1 - similarity).nonzero()
        inter_dists = dists.clone()
        intra_dists = dists.clone()
        inter_dists[ind_intra[:, 0], ind_intra[:, 1]] = 2
        intra_dists[ind_inter[:, 0], ind_inter[:, 1]] = -2
        neg_dist = inter_dists.min(dim=1)[0]
        pos_dist = intra_dists.max(dim=1)[0]

        pos = torch.relu(intra_dists - neg_dist.unsqueeze(1) + self.margin)
        neg = torch.relu(pos_dist.unsqueeze(1) - inter_dists + self.margin)

        return pos.sum() + neg.sum()


# criterion based on which we refine the embedding
class CenterMarginLoss(nn.Module):
    def __init__(self, margin):
        super(self.__class__, self).__init__()

        self.margin = margin

    def forward(self, center, pos, neg):
        pos_dists = 1.0 - center @ pos.transpose(0, 1)
        neg_dists = 1.0 - center @ neg.transpose(0, 1)

        # we minimize the distance between all images embeddings and the text embedding of their corresponding group
        pos = pos_dists
        # pos = torch.relu(pos_dists - neg_dists.max(dim=0)[0].detach() + self.margin)
        # each image, that is not in a given group should be farther away than all images that are in the group
        neg = torch.relu(pos_dists.max(dim=0)[0].detach() - neg_dists + self.margin)

        return pos.mean() + neg.mean()


class CrossEntropy(nn.Module):
    def __init__(self):
        super(self.__class__, self).__init__()

    def forward(self, center, pos, neg):
        # print(center.shape, pos.shape, neg.shape)
        pos_dists = center @ pos.transpose(0, 1)
        neg_dists = center @ neg.transpose(0, 1)

        pred = torch.cat([pos_dists, neg_dists], dim=-1) / 2 + 0.5
        target = torch.cat([torch.ones_like(pos_dists), torch.zeros_like(neg_dists)], dim=-1)
        loss = fn.binary_cross_entropy(pred, target)

        return loss
