import json
import os 
import tarfile
import shutil
import subprocess

def del_file_if_exists(path_to_file):
    if os.path.isfile(path_to_file):
        print(f"Overwriting {path_to_file}")
        os.remove(path_to_file)

def overwrite_dir_if_exists(path_to_dir):
    if os.path.exists(path_to_dir) and os.listdir(path_to_dir):
        print(f"Overwriting {path_to_dir}")
        shutil.rmtree(path_to_dir)
        os.makedirs(path_to_dir)


def get_ids_from_arxiv_or_pubmed(input_file, limit):
    id_list = []
    num_processed = 0
    with open(input_file, "r") as f:
        for line in f:
            item = json.loads(line)
            id_list.append(item["article_id"])
            num_processed += 1
            if num_processed == limit:
                break
    
    return id_list

def extract_pdf(url, output_path):
    """ Extract PDF based on URL

    Args:
        url (string): link to PDF 
        output_path (string): Path to output PDF file

    Returns:
        bool: True if extraction was successful, False otherwise
    """
    # command = f"wget -w 3 --random-wait -q -O {output_path} {url}"
    command = f"wget -w 3 --random-wait -O {output_path} '{url}'"
    subprocess.call(command, shell=True)
    
    if os.path.exists(output_path):
        return True
    return False 

def remove_processed_from_id_list(id_list, processed_log, failed_log=None):
    """ Remove already processed documents and documents that could not be processed
        from list

    Args:
        id_list (list): List of document IDs
        processed_log (string): Path to log containing IDs of processed documents
        failed_log (string): Path to log containing IDs of documents that could 
                             not be processed

    Returns:
        list: List of document IDs whose PDF and abstract have not been processed yet
    """
    if failed_log and os.path.isfile(failed_log):
        with open(failed_log, "r") as f:
            failed_to_process = f.read().splitlines()
    else:
        failed_to_process = []

    if os.path.isfile(processed_log):
        with open(processed_log, "r") as f:
            processed = f.read().splitlines()
    else:
        processed = []

    id_list = [
        doc_id for doc_id in id_list if (
            doc_id not in failed_to_process and doc_id not in processed
        )
    ] # remove ids whose articles could not be processed or whose have already been processed
    return id_list


def compress_dir(tar_path, output_folder):
    with tarfile.open(tar_path, "w:gz") as tar:
        tar.add(
            output_folder, 
            arcname=os.path.basename(output_folder)
        ) 

def get_doc_content(doc_path):
    doc_content = []
    with open(doc_path, 'r') as f:
        for line in f:
            content = line.split("\t")
            word = content[0]
            bbox = content[1:5]
            page_width, page_height = content[5:7]
            page_number = content[-1].rstrip()
            doc_content.append([word, bbox, page_width, page_height, page_number])

    return doc_content

def get_abstract(abstract_path, doc_id):
    with open(abstract_path, "r", encoding="utf-8") as f:
        for line in f:
            item = json.loads(line)
            if item["id"] == doc_id:
                return item["abstract"] 
    
    return None
