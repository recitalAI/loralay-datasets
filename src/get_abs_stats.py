from tqdm import tqdm 
import json 
import argparse
import os
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

def get_abs_length(
    abstract_file, 
    abstract_key, 
    input_folder=None, 
    file_extension=None,
):
    if input_folder is not None and file_extension is not None:
        input_files = list(Path(input_folder).rglob(f"*.{file_extension}"))
        valid_ids = [os.path.basename(os.path.normpath(fname))[:-(len(file_extension)+1)] for fname in input_files]

    all_abs_length = []
    len_valid = 0

    num_lines = sum(1 for line in open(abstract_file,'r'))
    with open(abstract_file, 'r', encoding='utf-8') as f:
        for line in tqdm(f, total=num_lines):
            item = json.loads(line)
            if input_folder is None or (item["id"] in valid_ids and abstract_key in item.keys()):
                abstract_length = len(item[abstract_key].split())
                all_abs_length.append(abstract_length)
                len_valid += 1

    return all_abs_length

def get_stats(args):
    all_abs_length = get_abs_length(
        args.abstract_file, 
        args.abstract_key, 
        input_folder=args.input_folder,
        file_extension=args.file_extension,
    )

    print(f"Stats for summary length in {args.abstract_file}")
    print("\tMin summary length: ", min(all_abs_length))
    print("\tMax summary length: ", max(all_abs_length))
    print("\tAvg summary length: ", round(np.mean(all_abs_length)))
    print("\tMedian summary length: ", round(np.median(all_abs_length)))

    quantile_5 = np.quantile(all_abs_length, q=0.05)
    quantile_1 = np.quantile(all_abs_length, q=0.01)
    print("\t5-th percentile: ", quantile_5)
    print("\t1st percentile: ", quantile_1)


    if args.plot_hist:
        plt.hist(all_abs_length, bins=30, facecolor='g')
        plt.xlabel('Number of words')
        plt.ylabel('Counts')
        plt.title(f'Histogram of summary length ({args.dataset_name})')
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(args.output_hist_fname, dpi=300)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--abstract_file",
        type=str,
        required=True,
    )
    parser.add_argument(
        "--abstract_key",
        type=str,
        default="abstract",
    )
    parser.add_argument(
        "--input_folder",
        type=str,
        default=None,
    )
    parser.add_argument(
        "--file_extension",
        type=str,
        default=None,
    )
    parser.add_argument(
        "--plot_hist", 
        action="store_true", 
    )
    parser.add_argument(
        "--output_hist_fname",
        type=str,
    )
    parser.add_argument(
        "--dataset_name",
        type=str,

    )

    args = parser.parse_args()

    get_stats(args)