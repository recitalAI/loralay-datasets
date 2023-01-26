import argparse 
import os 
import time 
from tqdm import tqdm
import subprocess
import urllib.request
import json
from src.utils import (
    del_file_if_exists,
    overwrite_dir_if_exists,
    extract_pdf
)
import langdetect
from langdetect import DetectorFactory

DetectorFactory.seed = 0


def get_last_idx(downloaded_log, failed_log):
    """ Get last index processed

    Args:
        downloaded_log (string): Path to log containing IDs of downloaded documents
        failed_log (string): Path to log containing IDs of documents that could 
                             not be downloaded

    Returns:
        int: Last index processed
    """
    with open(downloaded_log, "r") as f:
        lines = f.read().splitlines()
        last_downloaded_idx = lines[-1].split("\t")[0]

    with open(failed_log, "r") as f:
        lines = f.read().splitlines()
        last_failed_idx = lines[-1].split("\t")[0]

    return max(int(last_downloaded_idx), int(last_failed_idx))

def extract(args):
    if args.resume:
        print("Resuming download...")
        start_idx = get_last_idx(args.downloaded_output_log, args.failed_output_log) + 1
    else:
        start_idx = 0

    url = "https://api.archives-ouvertes.fr/search/" \
        "?q=*:*&" \
        "wt=json&" \
        "indent=True&" \
        f"fl=docid,files_s,{args.lang}_abstract_s,docType_s&" \
        f"fq=language_s:{args.lang}+submitType_s:file+docType_s:(ART%20OR%20COMM)&" \
        f"start={start_idx}&rows={args.n_docs - start_idx}"  
    
    print(f"Extracting documents from url {url}")

    response = urllib.request.urlopen(url).read().decode()
    data = json.loads(response)
    start_idx = int(data["response"]["start"])
    num_fails = 0

    for i, item in enumerate(tqdm(data["response"]["docs"])):
        successful_extraction = False 
        docid = str(item["docid"])
        if args.lang + "_abstract_s" in item and "files_s" in item:
            abstract_text = item[args.lang + "_abstract_s"][0].replace("\n", " ")  

            if abstract_text is not None:
                try:
                    lang_abstract = langdetect.detect(abstract_text)
                    if lang_abstract != "fr":
                        abstract_text = None
                except langdetect.lang_detect_exception.LangDetectException:
                    abstract_text = None 

            if abstract_text is not None:    
                pdf_output_path = os.path.join(args.pdf_output_dir, docid + ".pdf")        

                pdf_url = item["files_s"][0]
                pdf_extracted = extract_pdf(pdf_url, pdf_output_path)

                if pdf_extracted:
                    successful_extraction = True

        if not successful_extraction:
            num_fails += 1
            with open(args.failed_output_log, "a") as f:
                f.write(str(start_idx + i) + "\t" + docid + "\n")
        else:
            with open(args.abstract_output_path, "a") as fw:
                json.dump(
                    {"id": docid, "abstract": abstract_text}, fw, ensure_ascii=False
                )
                fw.write('\n')
            with open(args.downloaded_output_log, "a") as f:
                f.write(str(start_idx + i) + "\t" + docid + "\n")
        
        # time.sleep(1)

    num_total = len(data["response"]["docs"])
    print(f"Extracted abstract and PDF for {num_total - num_fails}/{num_total} articles.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--lang",
        type=str,
        required=True,
    )
    parser.add_argument(
        "--pdf_output_dir", 
        type=str,
        required=True,
    )
    parser.add_argument(
        "--abstract_output_path", 
        type=str,
        required=True,
    )
    parser.add_argument(
        "--downloaded_output_log",
        type=str,
        default="./downloaded.log"
    )
    parser.add_argument(
        "--failed_output_log",
        type=str,
        default="./failed_to_download.log"
    )
    parser.add_argument(
        "--n_docs",
        type=int,
        default=30,
    )
    parser.add_argument(
        "--resume",
        action="store_true", 
        help="Resume download."
    )
    parser.add_argument(
        "--overwrite_output_dir", 
        action="store_true", 
        help="Overwrite the output directory."
    )

    args = parser.parse_args()

    if args.resume and args.overwrite_output_dir:
        raise ValueError(
            f"Cannot use --resume and --overwrite_output_dir at the same time."
        )

    if (os.listdir(args.pdf_output_dir) or os.path.exists(args.abstract_output_path)) and not args.resume:
        if args.overwrite_output_dir:
            overwrite_dir_if_exists(args.pdf_output_dir)
            del_file_if_exists(args.abstract_output_path)
            del_file_if_exists(args.downloaded_output_log)
            del_file_if_exists(args.failed_output_log)            
        else:
            if os.listdir(args.pdf_output_dir):
                raise ValueError(
                    f"Output directory ({args.pdf_output_dir}) already exists and is not empty. Use --overwrite_output_dir to overcome."
                )
            if os.path.exists(args.abstract_output_path):
                raise ValueError(
                    f"Output file ({args.abstract_output_path}) already exists. Use --overwrite_output_dir to overcome."
                )


    extract(args)


