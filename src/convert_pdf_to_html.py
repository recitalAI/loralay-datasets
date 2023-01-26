from sys import prefix
from typing import Optional, Union
import subprocess
from pathlib import Path
import os
import shutil
import argparse
from tqdm import tqdm
from src.utils import remove_processed_from_id_list
from multiprocessing import Process
import PyPDF2
from PyPDF2 import PdfFileReader

def _is_valid_pdf(filepath, max_pages):
    try:
        with open(filepath, "rb") as pdf_file:
            pdf_reader = PdfFileReader(pdf_file, strict=False)
            num_pages = pdf_reader.numPages
        if max_pages > 0 and num_pages > max_pages: 
            return False 
        else:
            return True 
    except (PyPDF2.utils.PdfReadError, OSError, ValueError, AssertionError):
        return False 

def pdf2flowhtml(
    input_dir: Union[Path, str],
    pdf_folder: Union[Path, str],
    filename: Union[Path, str],
    output_folder: Union[Path, str],
    outputfile: Union[Path, str],
    use_docker: bool,
    first_page: int,
    max_pages: int,
) -> str:

    if use_docker:
        filepath = os.path.join(
            os.path.join(input_dir, pdf_folder), filename
        )
    else:
        filepath = os.path.join(pdf_folder, filename)
    if not _is_valid_pdf(filepath, max_pages=max_pages):
        return False

    if use_docker:
        command = "sudo docker run --rm -v {}:/pdf -v /tmp:/tmp poppler pdftotext -f {} -bbox-layout '{}' '{}'".format(
            os.path.abspath(input_dir),
            first_page,
            os.path.join(pdf_folder, filename),
            os.path.join(output_folder, outputfile)
        )
    else:
        command = "pdftotext -f {} -bbox-layout '{}' '{}'".format(
            first_page,
            os.path.join(pdf_folder, filename),
            os.path.join(output_folder, outputfile)
        )
    
    try: 
        subprocess.check_output(command, shell=True)
        return True
    except subprocess.CalledProcessError as e:
        return False


def convert(args):
    if args.use_docker:
        pdf_path = os.path.join(args.input_dir, args.pdf_folder)
    else:
        pdf_path = args.pdf_folder
    fnames = sorted(os.listdir(pdf_path))
    fnames = fnames[:args.n_docs] if args.n_docs > 0 else fnames 

    if args.resume:
        ext = ".pdf"
        fnames = [fname[:-len(ext)] for fname in fnames]
        print("Resuming conversion...")
        fnames = remove_processed_from_id_list(
            fnames, args.converted_output_log
        )
        fnames = fnames[1:]
        if not fnames:
            print(f"All documents in {pdf_path} have already been converted to HTML")
            return
        fnames = [fname + ext for fname in fnames]
        

    if args.num_processors > 0:
        processes = []
        partitions = [fnames[i: i+args.num_processors] for i in range(0, len(fnames), args.num_processors)]

        for part in partitions:
            for filename in tqdm(part):
                output_fname = filename[:-4] + ".html"
                p = Process(
                    target=pdf2flowhtml, 
                    args=(args.input_dir, args.pdf_folder, filename, args.output_folder, output_fname, args.use_docker, args.first_page, args.max_pages)
                )
                p.start()
                processes.append(p)
            for p in processes:
                p.join()
                
    else:
        for filename in tqdm(fnames, desc=f"Processing PDFs in {pdf_path}"):
            output_fname = filename[:-4] + ".html"
            if pdf2flowhtml(
                args.input_dir, 
                args.pdf_folder, 
                filename, 
                args.output_folder, 
                output_fname, 
                args.use_docker,
                args.first_page,
                args.max_pages
            ):
                with open(args.converted_output_log, "a") as f:
                    f.write(filename[:-4] + "\n")
            else:
                with open(args.failed_output_log, "a") as f:
                    f.write(filename[:-4] + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input_dir", 
        type=str,
        help="The input directory. If using docker, should be one "\
            "folder above the one containing the PDF files."
    )
    parser.add_argument(
        "--pdf_folder", 
        type=str,
        required=True,
    )
    parser.add_argument(
        "--output_folder", 
        type=str,
        default="html"
    )
    parser.add_argument(
        "--use_docker", 
        action="store_true", 
    )
    parser.add_argument(
        "--first_page", 
        type=int,
        default=1,
    )
    parser.add_argument(
        "--num_processors", 
        type=int,
        default=-1,
    )
    parser.add_argument(
        "--n_docs", 
        type=int,
        default=5,
    )
    parser.add_argument(
        "--max_pages", 
        type=int,
        default=-1,
    )
    parser.add_argument(
        "--converted_output_log",
        type=str,
        default="./converted_to_html.log"
    )
    parser.add_argument(
        "--failed_output_log",
        type=str,
        default="./failed_pdf_to_html.log"
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

    if args.use_docker:
        output_dir = os.path.join(args.input_dir, args.output_folder)
    else:
        output_dir = args.output_folder

    if os.listdir(output_dir) and not args.resume:
        if args.overwrite_output_dir:
            print(f"Overwriting {output_dir}")
            shutil.rmtree(output_dir)
            os.makedirs(output_dir)

            if os.path.isfile(args.converted_output_log):
                print(f"Overwriting {args.converted_output_log}")
                os.remove(args.converted_output_log)

        else:
            raise ValueError(
                f"Output directory ({output_dir}) already exists and is not empty. Use --overwrite_output_dir to overcome."
            )


    convert(args)