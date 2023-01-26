import argparse 
import os
import shutil
import json 
from datetime import datetime
from tqdm import tqdm

def split(args):
    with open(args.abstract_file, 'r') as f:
        lines = f.readlines()
    docs = [json.loads(line) for line in lines]

    docs_with_date = []
    docs_without_date = [] # Documents without a publication date will be put in the train set

    for doc in docs:
        if doc["publication_date"] is not None:
            docs_with_date.append(doc)
        else:
            docs_without_date.append(doc)

    sorted_docs_with_date = sorted(
        docs_with_date,
        key=lambda doc: datetime.strptime(doc["publication_date"], "%Y.%m.%d")
    )
    sorted_docs = docs_without_date + sorted_docs_with_date

    train_size = round(args.train_proportion * len(docs))
    val_size = round(args.val_proportion * len(docs))
    test_size = round(args.test_proportion * len(docs))

    train_docs = sorted_docs[:train_size]
    val_docs = sorted_docs[train_size: train_size + val_size]
    test_docs = sorted_docs[train_size + val_size:]

    train_folder = os.path.join(args.output_folder, "train")
    val_folder = os.path.join(args.output_folder, "val")
    test_folder = os.path.join(args.output_folder, "test")
    os.makedirs(train_folder)
    os.makedirs(val_folder)
    os.makedirs(test_folder)

    for doc in tqdm(train_docs, desc="Creating train split"):
        input_path = os.path.join(args.input_folder, doc["id"] + ".txt")
        output_path = os.path.join(train_folder, doc["id"] + ".txt")
        shutil.move(input_path, output_path)

    for doc in tqdm(val_docs, desc="Creating validation split"):
        input_path = os.path.join(args.input_folder, doc["id"] + ".txt")
        output_path = os.path.join(val_folder, doc["id"] + ".txt")
        shutil.move(input_path, output_path)
        
    for doc in tqdm(test_docs, desc="Creating test split"):
        input_path = os.path.join(args.input_folder, doc["id"] + ".txt")
        output_path = os.path.join(test_folder, doc["id"] + ".txt")
        shutil.move(input_path, output_path)
        

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input_folder",
        type=str,
        required=True,
    )
    parser.add_argument(
        "--abstract_file",
        type=str,
        required=True,
    )
    parser.add_argument(
        "--output_folder",
        type=str,
        required=True,
    )
    parser.add_argument(
        "--train_proportion",
        type=float,
        required=True
    )
    parser.add_argument(
        "--val_proportion",
        type=float,
        required=True
    )
    parser.add_argument(
        "--test_proportion",
        type=float,
        required=True
    )

    args = parser.parse_args()

    total_proportion = args.train_proportion + args.val_proportion + args.test_proportion

    if total_proportion != 1.:
        raise ValueError("Train/val/test proportions should sum to 1.")

    split(args)