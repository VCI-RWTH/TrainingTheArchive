import pandas as pd
from data import ImageDataset


if __name__ == '__main__':
    images_path = '../dataset/example/images/'
    meta_path = '../dataset/example/meta_data.csv'

    df = pd.read_csv(meta_path)
    df = df.applymap(str)
    df["encoding_id"] = -1

    dataset = ImageDataset(images_path, None)

    for i in range(len(dataset)):
        file = dataset.image_paths[i].split("/")[-1].split(".")[0]
        try:
            frame = df[df["object_id"] == file]
        except:
            continue

        if not frame.empty:
            df.at[frame.index[0], "encoding_id"] = i

    df.to_csv('../dataset/example/processed_meta_data.csv', index=False)
