import json
import os
import argparse
from tqdm import tqdm
from src.utils import (
    del_file_if_exists,
    overwrite_dir_if_exists,
    extract_pdf,
)
import random 
import time

def download_pdf_from_crawl(args):
    if args.resume_download:
        with open(args.downloaded_log) as f:   
            ids_downloaded = f.readlines()
        
    num_lines = sum(1 for line in open(args.input_file,'r'))
    with open(args.input_file, 'r') as f:
        for line in tqdm(f, total=num_lines):
            item = json.loads(line)
            output_path = os.path.join(args.output_dir, item["id"] + ".pdf") 
            if item["id"] in ids_downloaded:
                print("Skipping publication ", item["id"])
                continue 
            if "pdf_url" in item and item["pdf_url"] is not None:
                if extract_pdf(item["pdf_url"], output_path):
                    with open(args.downloaded_log, "a") as fw:
                        fw.write(item["id"] + "\n")
                else:
                    with open(args.not_downloaded_log, "a") as fw:
                        fw.write(item["id"] + "\n")
                waiting_time = random.uniform(0.5, 1.5) * 5
                print(f"Waiting {waiting_time} seconds")
                time.sleep(waiting_time)

            else:
                with open(args.not_downloaded_log, "a") as fw:
                    fw.write(item["id"] + "\n")
                
            

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input_file",
        type=str,
        required=True,
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        required=True,
    )
    parser.add_argument(
        "--downloaded_log",
        type=str,
        required=True,
    )
    parser.add_argument(
        "--not_downloaded_log",
        type=str,
        required=True,
    )
    parser.add_argument(
        "--overwrite_output_dir", 
        action="store_true", 
        help="Overwrite the output directory and log files."
    )
    parser.add_argument(
        "--resume_download", 
        action="store_true", 
    )

    args = parser.parse_args()
   
    if os.listdir(args.output_dir) and not args.resume_download:
        if args.overwrite_output_dir:
            overwrite_dir_if_exists(args.output_dir)
            del_file_if_exists(args.downloaded_log)
            del_file_if_exists(args.not_downloaded_log)
        else:
            raise ValueError(
                f"Output directory ({args.output_dir}) already exists and is not empty. Use --overwrite_output_dir to overcome."
            )
            
    download_pdf_from_crawl(args)
