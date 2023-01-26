
import argparse
import os
from tqdm import tqdm
import subprocess
from subprocess import PIPE
import re
import json
import xml.etree.ElementTree as ET
from pylatexenc.latex2text import LatexNodes2Text 
from src.utils import (
    del_file_if_exists,
    get_ids_from_arxiv_or_pubmed, 
    remove_processed_from_id_list,
    overwrite_dir_if_exists
)


def matches_first_id_scheme(id):
    """ Checks if id matches identifier scheme used until March 2007 
            e.g. astro-ph9702020

    Args:
        id (string): arXiv identifier 

    Returns:
        bool: True if id matches scheme, False otherwise
    """
    
    p = re.compile("^([a-z\-]*)(\d{7})$")
    m = p.match(id)
    return m

def extract_pdf(arxiv_id, pdf_output_path):
    """ Extract PDF from Google Cloud Storage buckets using gsutil

    Args:
        arxiv_id (string): arXiv identifier
        pdf_output_path (string): Path to output PDF 

    Returns:
        bool: True if PDF has been correctly extracted, False otherwise
    """
    m = matches_first_id_scheme(arxiv_id)
    if m:
        command = [
            "gsutil",
            "-q",
            "ls",
            f"gs://arxiv-dataset/arxiv/{m.group(1)}/pdf/{m.group(2)[:4]}/{m.group(2)}v*.pdf"
        ]
    else:
        p = re.compile("^(\d{4})\.(\d{4,5})$")
        m = p.match(arxiv_id)
        assert m, print(arxiv_id)
        command = [
            "gsutil",
            "-q",
            "ls",
            f"gs://arxiv-dataset/arxiv/arxiv/pdf/{m.group(1)}/{arxiv_id}v*.pdf"
        ]

    p = subprocess.Popen(command, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    output, err = p.communicate()

    versions = output.decode("utf-8").split("\n")
    versions = [v for v in versions if v] # remove empty string

    if len(versions) == 0:
        return False

    if m:
        sorted_versions = sorted(
            versions, 
            key=lambda x: int(re.match(".*" + re.escape(m.group(2)) + "v([0-9]+).pdf", x).group(1))
        )
    else:
        sorted_versions = sorted(
            versions, 
            key=lambda x: int(re.match(".*" + re.escape(arxiv_id) + "v([0-9]+).pdf", x).group(1))
        )

    command = f"gsutil -q cp {sorted_versions[-1]} {pdf_output_path}"

    subprocess.call(command, shell=True)

    if os.path.exists(pdf_output_path):
        return True 
    return False

def extract(args):
    id_list = get_ids_from_arxiv_or_pubmed(args.input_file, args.n_docs)

    if args.resume:
        print("Resuming extraction...")
        id_list = remove_processed_from_id_list(
            id_list, args.downloaded_output_log, failed_log=args.failed_output_log
        )

        if not id_list:
            print(f"All articles in {args.input_file} have already been extracted")
            return 

    print(f"Extracting {len(id_list)} articles from arXiv, using IDs in {args.input_file}")

    remaining_ids = id_list.copy()
    num_fails = 0

    with open(args.metadata_file, "r") as f:
        for line in tqdm(f):
            metadata = json.loads(line)
            arxiv_id = metadata["id"].replace("/", "")
            
            if arxiv_id in id_list:
                pdf_output_path = os.path.join(args.pdf_output_dir, arxiv_id + ".pdf")
                pdf_extracted = extract_pdf(arxiv_id, pdf_output_path)

                if pdf_extracted: 
                    abstract_text = metadata["abstract"].replace("\n", " ")
                    try:
                        abstract_text = LatexNodes2Text().latex_to_text(abstract_text)
                        abstract_extracted = True
                    except IndexError:
                        abstract_extracted = False
                        num_fails += 1

                    
                if pdf_extracted and abstract_extracted:
                    with open(args.abstract_output_path, 'a') as outfile:
                        json.dump(
                            {"id": arxiv_id, "abstract": abstract_text}, 
                            outfile
                        )
                        outfile.write('\n')
                    with open(args.downloaded_output_log, "a") as f:
                        f.write(arxiv_id + "\n")
                else:
                    num_fails += 1
                    with open(args.failed_output_log, "a") as f:
                        f.write(arxiv_id + "\n")
                
                remaining_ids.remove(arxiv_id)

                if len(remaining_ids) == 0:
                    break

    for arxiv_id in remaining_ids: # articles whose abstracts have not been found
        num_fails += 1
        with open(args.failed_output_log, "a") as f:
            f.write(arxiv_id + "\n")


    print(f"Extracted abstract and PDF for {len(id_list) - num_fails}/{len(id_list)} articles.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input_file", 
        type=str,
        required=True,
        help="The input file containing the IDs to extract."
    )
    parser.add_argument(
        "--metadata_file", 
        type=str,
        required=True,
        help="The metadata file containing the abstracts to extract."
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
        default=5,
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
                    f"Output file ({args.abstract_output_path}) already exists and is not empty. Use --overwrite_output_dir to overcome."
                )

    extract(args)
