import sys
from argparse import ArgumentParser

import pandas as pd

sys.path.insert(0, '..')
from data import ImageDataset


# this script is made specifically for the Ludwigforum metadata and needs to be updated for any other source
if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("--image-dir", type=str,
                        default='/clusterarchive/mibing/datasets/Lufo_images/TTA_LuFo_25-5-22/TTA_Standardbilder_Sammlung/')
    parser.add_argument("--meta-path", type=str,
                        default='/clusterarchive/mibing/datasets/Lufo_images/TTA_LuFo_25-5-22/Export_TTA_erweitert.xlsx')
    parser.add_argument("--output-path", type=str,
                        default='/clusterarchive/mibing/datasets/Lufo_images/TTA_LuFo_25-5-22/meta_data.csv')
    args = parser.parse_args()

    df = pd.read_excel(args.meta_path, dtype={'Jahr': str})
    df['Jahr'] = df['Jahr'].astype(int, errors='ignore')
    df = df.applymap(str)
    df["encoding_id"] = -1

    dataset = ImageDataset('/clusterarchive/mibing/datasets/Lufo_images/TTA_LuFo_25-5-22/TTA_Standardbilder_Sammlung',
                           None)

    for i in range(len(dataset)):
        path = dataset.image_paths[i].split("/")[-1].split(".")[0]
        try:
            frame = df[df["Obj_ Id_"] == path]
        except:
            continue
        if not frame.empty:
            df.at[frame.index[0], "encoding_id"] = i

    df.to_csv(args.output_path, index=False)
