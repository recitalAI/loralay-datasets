

import os
import argparse
from tqdm import tqdm
import shutil 
import json

def divide(args):
    num_es = 0
    num_pt = 0
    num_lines = sum(1 for line in open(args.abstract_file,'r'))
    with open(args.abstract_file, "r") as f:
        for line in tqdm(f, total=num_lines):
            item = json.loads(line)
            if item["pdf_lang"] in ["es", "pt"] and not os.path.exists(os.path.join(args.input_folder, item["id"] + ".pdf")):
                continue 
            if item["pdf_lang"] == "es":
                lang = "es"
                num_es += 1
            elif item["pdf_lang"] == "pt":
                lang = "pt"
                num_pt += 1
            if item["pdf_lang"] in ["es", "pt"]:
                shutil.move(
                    os.path.join(args.input_folder, item["id"] + ".pdf"),
                    os.path.join(
                        os.path.join(args.input_folder, lang), 
                        item["id"] + ".pdf"
                    )
                )

    print("Spanish: {}/{}".format(num_es, num_es + num_pt))
    print("Portuguese: {}/{}".format(num_pt, num_es + num_pt))


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

    args = parser.parse_args()

    divide(args)