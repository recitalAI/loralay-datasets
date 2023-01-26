import os
import argparse
from tqdm import tqdm
import matplotlib.pyplot as plt
import numpy as np
import PyPDF2
from PyPDF2 import PdfFileReader
from pathlib import Path

def count_num_pages_from_pdf(input_folder):
    # input_files = os.listdir(input_folder)
    input_files = list(Path(input_folder).rglob("*.pdf"))

    all_num_pages = []

    for fpath in tqdm(input_files):
        try:
            # with open(os.path.join(input_folder, fpath), "rb") as pdf_file:
            with open(fpath, 'rb') as pdf_file:
                pdf_reader = PdfFileReader(pdf_file, strict=False)
                all_num_pages.append(pdf_reader.numPages)
        except (PyPDF2.utils.PdfReadError, OSError, KeyError, ValueError, TypeError, AssertionError):
            continue 

    return all_num_pages

def count_num_pages_from_txt(input_folder):
    # input_files = os.listdir(input_folder)
    input_files = list(Path(input_folder).rglob("*.txt"))

    all_num_pages = []

    for fpath in tqdm(input_files):
        # with open(os.path.join(input_folder, fpath), "r") as f:
        with open(fpath, 'r') as f:
            lines = f.readlines()
        last_page = int(lines[-1].split("\t")[-1])
        all_num_pages.append(last_page)

    return all_num_pages

def get_stats(args):
    if args.file_extension == "pdf":
        all_num_pages = count_num_pages_from_pdf(args.input_folder)
    elif args.file_extension == "txt":
        all_num_pages = count_num_pages_from_txt(args.input_folder)
    else:
        raise ValueError(f"Files in {args.input_folder} must have either '.pdf' or '.txt' extension.")

    print(f"Stats for {args.input_folder}")
    print("\tMin # pages: ", min(all_num_pages))
    print("\tMax # pages: ", max(all_num_pages))
    print("\tAvg # pages: ", round(np.mean(all_num_pages)))
    print("\tMedian # pages: ", round(np.median(all_num_pages)))
    print("\tTotal # pages: ", round(np.sum(all_num_pages)))

    quantile_95 = np.quantile(all_num_pages, q=0.95)
    quantile_99 = np.quantile(all_num_pages, q=0.99)
    print("\t95-th percentile: ", quantile_95)
    print("\t99-th percentile: ", quantile_99)

    if args.plot_hist:
        plt.hist(all_num_pages)
        plt.xlabel('Number of pages')
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
        "--file_extension",
        type=str,
        required=True,
    )
    parser.add_argument(
        "--plot_hist", 
        action="store_true", 
    )
    parser.add_argument(
        "--dataset_name",
        type=str,
    )
    parser.add_argument(
        "--output_hist_fname",
        type=str,
    )

    args = parser.parse_args()

    get_stats(args)