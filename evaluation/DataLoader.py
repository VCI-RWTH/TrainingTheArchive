import os
import random
from glob import glob

import numpy as np
import pandas as pd
import torch.utils.data
from PIL import Image, ImageFile
from tqdm import trange

ImageFile.LOAD_TRUNCATED_IMAGES = True


class FewShotDataset(object):
    def __init__(self, shot_num, way_num, episode_test_sample_num, shuffle_images=False, transform=None):
        self.shot_num = shot_num
        self.way_num = way_num
        self.episode_test_sample_num = episode_test_sample_num
        self.num_samples_per_class = episode_test_sample_num + shot_num
        self.shuffle_images = shuffle_images
        self.transform = transform
        self.paths, self.label = [], []

    def __len__(self):
        return len(self.paths)

    def create_meta_sets(self, image_path, meta_table, criterion, n_classes, episode_num):
        assert (criterion in ['Tags', 'Title', 'Artist Alpha Sort', 'Medium', 'Object Name',
                              'Classification', 'Country', 'Culture', 'image'])
        df = pd.read_csv(meta_table, delimiter='\t')

        label = df[criterion]
        top_label = label.dropna().value_counts()[:n_classes].index.tolist()

        lbls = []
        for _ in trange(episode_num):
            restricted_folder = [item for item in top_label if item not in lbls]
            lbls = random.sample(restricted_folder, self.way_num)
            episode_paths = []
            episode_label = []
            for lbl in lbls:
                frames = df.loc[label == lbl].sample(self.num_samples_per_class, replace=False)
                episode_paths.append([image_path + p for p in frames['image'].tolist()])
                episode_label.append(frames[criterion].tolist())
            self.paths.append(episode_paths)
            self.label.append(episode_label)

    def create_artigo_sets(self, image_path, meta_table, tags, image_to_tag, n_classes, episode_num):
        df_im_to_tag = pd.read_csv(image_to_tag, delimiter=',')
        df_tags = pd.read_csv(tags, delimiter=',')
        df_meta = pd.read_csv(meta_table, delimiter=',')

        df_im_to_tag = df_im_to_tag.loc[df_im_to_tag['frequency'] > 10]
        label = df_im_to_tag['tag_id']
        top_label = label.dropna().value_counts()[:n_classes].index.tolist()
        label_names = [df_tags[df_tags['id'] == idx]['name'].item() for idx in top_label]

        lbls = []
        for _ in trange(episode_num):
            restricted_folder = [item for item in list(enumerate(top_label)) if item not in lbls]
            lbls = random.sample(restricted_folder, self.way_num)
            episode_paths = []
            episode_label = []
            for i, lbl in lbls:
                while True:
                    frames = df_im_to_tag.loc[label == lbl].sample(self.num_samples_per_class, replace=False)
                    paths = [image_path + p for p in
                             df_meta.loc[df_meta['id'].isin(frames['resource_id'])]['path'].tolist()]
                    if len(paths) == self.num_samples_per_class:
                        break
                episode_paths.append(paths)
                episode_label.append([label_names[i]] * self.num_samples_per_class)
            self.paths.append(episode_paths)
            self.label.append(episode_label)

    def create_wikiart_sets(self, image_path, n_classes, episode_num):
        directories = sorted(glob(image_path + "/*"))
        label = [" ".join(d.split("/")[-1].split("_")) for d in directories]

        lbls = []
        for _ in trange(episode_num):
            restricted_folder = [item for item in list(enumerate(label)) if item not in lbls]
            lbls = random.sample(restricted_folder, self.way_num)
            episode_paths = []
            episode_label = []
            for i, lbl in lbls:
                images = sorted(glob(directories[i] + "/*"))
                while True:
                    paths = random.sample(images, self.num_samples_per_class)
                    if len(paths) == self.num_samples_per_class:
                        break
                episode_paths.append(paths)
                episode_label.append([lbl] * self.num_samples_per_class)
            self.paths.append(episode_paths)
            self.label.append(episode_label)

    def get_batch(self, idx=0):
        image_paths = self.paths[idx]
        label = self.label[idx]

        shot_img = []
        shot_lbl = []
        test_img = []
        test_lbl = []
        for i in range(self.way_num):
            perm = np.random.permutation(self.num_samples_per_class)
            shot_way = []
            test_way = []
            for j in range(self.num_samples_per_class):
                if j < self.shot_num:
                    shot_img.append(self.transform(Image.open(image_paths[i][perm[j]])))
                    shot_way.append(label[i][perm[j]])
                else:
                    test_img.append(self.transform(Image.open(image_paths[i][perm[j]])))
                    test_way.append(label[i][perm[j]])
            shot_lbl.append(shot_way)
            test_lbl.append(test_way)

        return torch.stack(shot_img), shot_lbl, torch.stack(test_img), test_lbl


class MiniImageNetDataLoader(object):
    def __init__(self, shot_num, way_num, episode_test_sample_num, shuffle_images=False, transform=None):
        self.shot_num = shot_num
        self.way_num = way_num
        self.episode_test_sample_num = episode_test_sample_num
        self.num_samples_per_class = episode_test_sample_num + shot_num
        self.shuffle_images = shuffle_images
        self.transform = transform
        metatrain_folder = '/clusterarchive/mibing/datasets/mini-imagenet/train'
        metaval_folder = '/clusterarchive/mibing/datasets/mini-imagenet/val'
        metatest_folder = '/clusterarchive/mibing/datasets/mini-imagenet/test'
        self.label_translate = pd.read_csv("/clusterarchive/mibing/datasets/mini-imagenet/labels.csv", delimiter=' ')

        npy_dir = '/clusterarchive/mibing/datasets/mini-imagenet/'
        if not os.path.exists(npy_dir):
            os.mkdir(npy_dir)

        self.npy_base_dir = npy_dir + str(self.shot_num) + 'shot_' + str(self.way_num) + 'way_' + str(
            episode_test_sample_num) + 'shuffled_' + str(self.shuffle_images) + '/'
        if not os.path.exists(self.npy_base_dir):
            os.mkdir(self.npy_base_dir)

        self.metatrain_folders = [os.path.join(metatrain_folder, label) \
                                  for label in os.listdir(metatrain_folder) \
                                  if os.path.isdir(os.path.join(metatrain_folder, label)) \
                                  ]
        self.metaval_folders = [os.path.join(metaval_folder, label) \
                                for label in os.listdir(metaval_folder) \
                                if os.path.isdir(os.path.join(metaval_folder, label)) \
                                ]
        self.metatest_folders = [os.path.join(metatest_folder, label) \
                                 for label in os.listdir(metatest_folder) \
                                 if os.path.isdir(os.path.join(metatest_folder, label)) \
                                 ]

    def get_images(self, paths, labels, nb_samples=None, shuffle=True):
        if nb_samples is not None:
            sampler = lambda x: random.sample(x, nb_samples)
        else:
            sampler = lambda x: x
        labels = [self.label_translate.loc[self.label_translate['train'] == path.split("/")[-1]]['class'].item() for
                  path in paths]
        images = [(i, os.path.join(path, image)) \
                  for i, path in zip(labels, paths) \
                  for image in sampler(os.listdir(path))]
        if shuffle:
            random.shuffle(images)
        return images

    def generate_data_list(self, phase='train', episode_num=None):
        if phase == 'train':
            folders = self.metatrain_folders
            if episode_num is None:
                episode_num = 20000
            if not os.path.exists(self.npy_base_dir + '/train_filenames.npy'):
                print('Generating train filenames')
                all_filenames = []
                all_labels = []
                sampled_character_folders = []
                for _ in trange(episode_num):
                    restricted_folder = [item for item in folders if item not in sampled_character_folders]
                    sampled_character_folders = random.sample(restricted_folder, self.way_num)
                    random.shuffle(sampled_character_folders)
                    labels_and_images = self.get_images(sampled_character_folders, range(self.way_num),
                                                        nb_samples=self.num_samples_per_class,
                                                        shuffle=self.shuffle_images)
                    labels = [li[0] for li in labels_and_images]
                    filenames = [li[1] for li in labels_and_images]
                    all_filenames.extend(filenames)
                    all_labels.extend(labels)
                np.save(self.npy_base_dir + '/train_labels.npy', all_labels)
                np.save(self.npy_base_dir + '/train_filenames.npy', all_filenames)
                print('Train filename and label lists are saved')

        elif phase == 'val':
            folders = self.metaval_folders
            if episode_num is None:
                episode_num = 600
            if not os.path.exists(self.npy_base_dir + '/val_filenames.npy'):
                print('Generating val filenames')
                all_filenames = []
                all_labels = []
                sampled_character_folders = []
                for _ in trange(episode_num):
                    restricted_folder = [item for item in folders if item not in sampled_character_folders]
                    sampled_character_folders = random.sample(restricted_folder, self.way_num)
                    labels_and_images = self.get_images(sampled_character_folders, range(self.way_num),
                                                        nb_samples=self.num_samples_per_class,
                                                        shuffle=self.shuffle_images)
                    labels = [li[0] for li in labels_and_images]
                    filenames = [li[1] for li in labels_and_images]
                    all_filenames.extend(filenames)
                    all_labels.extend(labels)
                np.save(self.npy_base_dir + '/val_labels.npy', all_labels)
                np.save(self.npy_base_dir + '/val_filenames.npy', all_filenames)
                print('Val filename and label lists are saved')

        elif phase == 'test':
            folders = self.metatest_folders
            if episode_num is None:
                episode_num = 600
            if not os.path.exists(self.npy_base_dir + '/test_filenames.npy'):
                print('Generating test filenames')
                all_filenames = []
                all_labels = []
                sampled_character_folders = []
                for _ in trange(episode_num):
                    restricted_folder = [item for item in folders if item not in sampled_character_folders]
                    sampled_character_folders = random.sample(restricted_folder, self.way_num)
                    labels_and_images = self.get_images(sampled_character_folders, range(self.way_num),
                                                        nb_samples=self.num_samples_per_class,
                                                        shuffle=self.shuffle_images)
                    labels = [li[0] for li in labels_and_images]
                    filenames = [li[1] for li in labels_and_images]
                    all_filenames.extend(filenames)
                    all_labels.extend(labels)
                np.save(self.npy_base_dir + '/test_labels.npy', all_labels)
                np.save(self.npy_base_dir + '/test_filenames.npy', all_filenames)
                print('Test filename and label lists are saved')
        else:
            print('Please select vaild phase')

    def load_list(self, phase='train'):
        if phase == 'train':
            self.train_filenames = np.load(self.npy_base_dir + 'train_filenames.npy').tolist()
            self.train_labels = np.load(self.npy_base_dir + 'train_labels.npy').tolist()

        elif phase == 'val':
            self.val_filenames = np.load(self.npy_base_dir + 'val_filenames.npy').tolist()
            self.val_labels = np.load(self.npy_base_dir + 'val_labels.npy').tolist()

        elif phase == 'test':
            self.test_filenames = np.load(self.npy_base_dir + 'test_filenames.npy').tolist()
            self.test_labels = np.load(self.npy_base_dir + 'test_labels.npy').tolist()

        elif phase == 'all':
            self.train_filenames = np.load(self.npy_base_dir + 'train_filenames.npy').tolist()
            self.train_labels = np.load(self.npy_base_dir + 'train_labels.npy').tolist()

            self.val_filenames = np.load(self.npy_base_dir + 'val_filenames.npy').tolist()
            self.val_labels = np.load(self.npy_base_dir + 'val_labels.npy').tolist()

            self.test_filenames = np.load(self.npy_base_dir + 'test_filenames.npy').tolist()
            self.test_labels = np.load(self.npy_base_dir + 'test_labels.npy').tolist()

        else:
            print('Please select vaild phase')

    def process_batch(self, input_filename_list, input_label_list, batch_sample_num, reshape_with_one=True):
        # new_path_list = []
        # new_label_list = []
        # for k in range(batch_sample_num):
        #     class_idxs = list(range(0, self.way_num))
        #     # random.shuffle(class_idxs)
        #     for class_idx in class_idxs:
        #         true_idx = class_idx * batch_sample_num + k
        #         new_path_list.append(input_filename_list[true_idx])
        #         new_label_list.append(input_label_list[true_idx])

        img_list = []
        for filepath in input_filename_list:
            img_list.append(self.transform(Image.open(filepath)))
            # this_img = imageio.imread(filepath)
            # this_img = this_img / 255.0
            # img_list.append(this_img)

        img_array = torch.stack(img_list)
        label_array = input_label_list
        # if reshape_with_one:
        #     img_array = np.array(img_list)
        #     label_array = self.one_hot(np.array(new_label_list)).reshape([1, self.way_num * batch_sample_num, -1])
        # else:
        #     img_array = np.array(img_list)
        #     label_array = self.one_hot(np.array(new_label_list)).reshape([self.way_num * batch_sample_num, -1])
        return img_array, label_array

    def one_hot(self, inp):
        n_class = inp.max() + 1
        n_sample = inp.shape[0]
        out = np.zeros((n_sample, n_class))
        for idx in range(n_sample):
            out[idx, inp[idx]] = 1
        return out

    def get_batch(self, phase='train', idx=0):
        if phase == 'train':
            all_filenames = self.train_filenames
            labels = self.train_labels
        elif phase == 'val':
            all_filenames = self.val_filenames
            labels = self.val_labels
        elif phase == 'test':
            all_filenames = self.test_filenames
            labels = self.test_labels
        else:
            print('Please select vaild phase')
            return

        one_episode_sample_num = self.num_samples_per_class * self.way_num
        this_task_filenames = all_filenames[idx * one_episode_sample_num:(idx + 1) * one_episode_sample_num]
        this_task_labels = labels[idx * one_episode_sample_num:(idx + 1) * one_episode_sample_num]
        epitr_sample_num = self.shot_num
        epite_sample_num = self.episode_test_sample_num

        this_task_tr_filenames = []
        this_task_tr_labels = []
        this_task_te_filenames = []
        this_task_te_labels = []
        for class_k in range(self.way_num):
            this_class_filenames = this_task_filenames[
                                   class_k * self.num_samples_per_class:(class_k + 1) * self.num_samples_per_class]
            this_class_label = this_task_labels[
                               class_k * self.num_samples_per_class:(class_k + 1) * self.num_samples_per_class]
            this_task_tr_filenames += this_class_filenames[0:epitr_sample_num]
            this_task_tr_labels.append(this_class_label[0:epitr_sample_num])
            this_task_te_filenames += this_class_filenames[epitr_sample_num:]
            this_task_te_labels.append(this_class_label[epitr_sample_num:])

        this_inputa, this_labela = self.process_batch(this_task_tr_filenames, this_task_tr_labels, epitr_sample_num,
                                                      reshape_with_one=False)
        this_inputb, this_labelb = self.process_batch(this_task_te_filenames, this_task_te_labels, epite_sample_num,
                                                      reshape_with_one=False)

        return this_inputa, this_labela, this_inputb, this_labelb
