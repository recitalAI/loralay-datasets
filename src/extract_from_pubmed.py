import argparse 
import os 
import subprocess
import tarfile 
import json
from tqdm import tqdm
import xml.etree.ElementTree as ET
import urllib.request
import logging
from pylatexenc.latex2text import LatexNodes2Text 
from src.utils import (
    del_file_if_exists,
    get_ids_from_arxiv_or_pubmed, 
    remove_processed_from_id_list,
    del_file_if_exists,
    overwrite_dir_if_exists,
    extract_pdf
)
import zlib

logging.disable(logging.CRITICAL)

def extract_abstract(url):
    """ Extract abstract using the BioC API

    Args:
        url (string): URL of article abstract in BioC XML format

    Returns:
        string: Abstract text 
    """
    response = urllib.request.urlopen(url).read()
    tree = ET.fromstring(response)
    abstract_nodes = tree.findall(".//passage[infon = 'ABSTRACT']/text")
    if not abstract_nodes:
        return None 
    else:
        abstract_text = " ".join(a.text for a in abstract_nodes)
        return abstract_text

def extract_pdf_from_tar_url(url, output_path, tar_path):
    """ Extract PDF from tar archive 

    Args:
        url (string): FTP link to tar archive containing PDF
        output_path (string): Path to output PDF file
        tar_path (string): Path to tar archive

    Returns:
        bool: True if extraction was successful, False otherwise
    """
    command = f"wget -q -O {tar_path} {url}"
    subprocess.call(command, shell=True)

    tar = tarfile.open(tar_path)
    try:
        pdf_fname = [t.name for t in tar.getmembers() if ".pdf" in t.name]
    except zlib.error:
        return False

    if len(pdf_fname) == 1:
        pdf_contents = tar.extractfile(pdf_fname[0]).read()
        with open(output_path, "wb") as fw:
            fw.write(pdf_contents)
        os.remove(tar_path)
        return True 
    return False 

def find_ftp_url(oa_url):
    """ Extract FTP URL from PMC OA URL (https://www.ncbi.nlm.nih.gov/pmc/tools/ftp/)

    Args:
        oa_url (string): OA URL providing the article location on the FTP site 

    Returns:
        string: link to the article (PDF or tar) location on the FTP site
    """
    response = urllib.request.urlopen(oa_url).read()
    tree = ET.fromstring(response)

    links = tree.findall(".//link")    
    if len(links) > 1:
        return tree.find('.//link[@format="pdf"]').get("href")
    elif len(links) == 1:
        return links[0].get("href")
    else:
        return None


def extract(args):
    id_list = get_ids_from_arxiv_or_pubmed(args.input_file, args.n_docs)

    if args.resume:
        print("Resuming extraction...")
        id_list = remove_processed_from_id_list(
            id_list, args.downloaded_output_log, args.failed_output_log
        )

        if not id_list:
            print(f"All articles in {args.input_file} have already been extracted")
            return 

    print(f"Extracting {len(id_list)} articles from PubMed, using IDs in {args.input_file}")
    num_fails = 0
    
    for pmcid in tqdm(id_list):
        failed_extraction = False

        oa_url = f"https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi?id={pmcid}"
        ftp_url = find_ftp_url(oa_url)
        output_path = os.path.join(args.pdf_output_dir, pmcid + ".pdf")

        if not ftp_url:
            pdf_extracted = False
        elif ".pdf" in ftp_url:
            pdf_extracted = extract_pdf(ftp_url, output_path) 
        else:
            tar_path = os.path.join(args.extract_output_dir, pmcid + ".tar.gz")

            pdf_extracted = extract_pdf_from_tar_url(ftp_url, output_path, tar_path)

        if pdf_extracted:
            abstract_text = extract_abstract(
                f"https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_xml/{pmcid}/unicode"
            )
            if abstract_text: 
                abstract_text = LatexNodes2Text().latex_to_text(abstract_text.replace("\n", " "))
                with open(args.abstract_output_path, "a") as outfile:
                    json.dump(
                        {"id": pmcid, "abstract": abstract_text}, 
                        outfile
                    )
                    outfile.write('\n')
            else:
                failed_extraction = True 
                os.remove(output_path) # pdf has been extracted, delete it
        else:
            failed_extraction = True

        if failed_extraction:
            num_fails += 1
            with open(args.failed_output_log, "a") as f:
                f.write(pmcid + "\n")
        else:
            with open(args.downloaded_output_log, "a") as f:
                f.write(pmcid + "\n")
        
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
        "--extract_output_dir", 
        type=str,
        default="./tmp",
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

    if (
        os.listdir(args.pdf_output_dir) or os.path.exists(args.abstract_output_path) or os.path.exists(args.extract_output_dir)
    ) and not args.resume:
        if args.overwrite_output_dir:
            overwrite_dir_if_exists(args.pdf_output_dir)
            overwrite_dir_if_exists(args.extract_output_dir)
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
            if os.listdir(args.extract_output_dir):
                raise ValueError(
                    f"Output directory ({args.extract_output_dir}) already exists and is not empty. Use --overwrite_output_dir to overcome."
                )

    extract(args)