import os
import argparse
from tqdm import tqdm
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

def count_num_words(input_folder):
    # input_files = os.listdir(input_folder)
    input_files = list(Path(input_folder).rglob("*.txt"))

    all_num_words = []

    for fpath in tqdm(input_files):
        # with open(os.path.join(input_folder, fpath), "r") as f:
        with open(fpath, 'r') as f:
            lines = f.readlines()
        all_num_words.append(len(lines))

    return all_num_words

def get_stats(args):
    all_num_words = count_num_words(args.input_folder)
    
    print(f"Stats for {args.input_folder}")
    print("\tMin # words: ", min(all_num_words))
    print("\tMax # words: ", max(all_num_words))
    print("\tAvg # words: ", round(np.mean(all_num_words)))
    print("\tMedian # words: ", round(np.median(all_num_words)))
    print("\tTotal # words: ", round(np.sum(all_num_words)))

    quantile_1 = np.quantile(all_num_words, q=0.01)
    quantile_5 = np.quantile(all_num_words, q=0.05)
    print("\t1st percentile: ", quantile_1)
    print("\t5-th percentile: ", quantile_5)
    quantile_95 = np.quantile(all_num_words, q=0.95)
    quantile_99 = np.quantile(all_num_words, q=0.99)
    print("\t95-th percentile: ", quantile_95)
    print("\t99-th percentile: ", quantile_99)

    if args.plot_hist:
        plt.hist(all_num_words, bins=30, color="red")
        plt.xlabel('Number of words')
        plt.ylabel('Counts')
        plt.title(args.dataset_name)
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(args.output_hist_fname, dpi=300)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input_folder",
        type=str,
        required=True,
    )
    parser.add_argument(
        "--dataset_name",
        type=str,
    )
    parser.add_argument(
        "--plot_hist", 
        action="store_true", 
    )
    parser.add_argument(
        "--output_hist_fname",
        type=str,
    )

    args = parser.parse_args()

    get_stats(args)