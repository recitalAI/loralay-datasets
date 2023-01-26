import os
import shutil
import argparse
from tqdm import tqdm
from lxml.etree import iterparse
import re
import logging
from src.utils import remove_processed_from_id_list, compress_dir

logger = logging.getLogger(__name__)

REF_MAPPING = {
    "de": ["bibliografie","literatur", "referenzen"],
    "es": ["referencias", "bibliografía"],
    "fr": ["bibliographie", "références"],
    "it": ["bibliografia"],
    "pt": ["referências", "bibliografia"],
    "ru": ["литература"],
}

def remove_special_chars(text):
    return re.sub('[^a-zA-Z0-9*\s]', '', text)

def clean_text(text):
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"’", "'", text)
    return text

def normalize_bbox(bbox, size):
    return (
        int(1000 * bbox[0] / size[0]),
        int(1000 * bbox[1] / size[1]),
        int(1000 * bbox[2] / size[0]),
        int(1000 * bbox[3] / size[1]),
    )

def skip_first_page(page):
    text = [elem[0] for elem in page]
    text = " ".join(text)

    if "HAL is a multi-disciplinary open access archive" in text:
        return True 

    return False

def extract_text_from_tree(file_path, do_normalize_bbox=False, remove_ref=False):
    doc = []

    cur_page = []
    page_width = None
    page_height = None
    ref_page_idx = None
    ref_start_idx_in_page = None

    with open(file_path, 'rb') as f:
        for _, element in iterparse(f, events=("start", "end"), recover=True):
            if "word" in element.tag and element.text:
                word = clean_text(element.text) if element.text else None
                if word:
                    if element.attrib:
                        if page_width == 0 or page_height == 0:
                            continue
                        xmin = round(float(element.attrib['xMin']))
                        xmax = round(float(element.attrib['xMax']))
                        ymin = round(float(element.attrib['yMin']))
                        ymax = round(float(element.attrib['yMax']))

                        xmin, ymin = max(0, xmin), max(0, ymin) # set to 0 if < 0 
                        xmax, ymax = min(page_width, xmax), min(page_height, ymax) # set to max if > max

                        xmin = min(xmin, page_width) # set to max if > max 
                        ymin = min(ymin, page_height) 
                        xmax = max(0, xmax) # set to 0 if < 0
                        ymax = max(0, ymax)

                        if xmin > xmax: # swap if xmin > xmax
                            xmin, xmax = xmax, xmin
                        if ymin > ymax:
                            ymin, ymax = ymax, ymin

                        bbox = tuple([xmin, ymin, xmax, ymax])
                        if do_normalize_bbox:
                            bbox = normalize_bbox(bbox, (page_width, page_height))

                        cur_page.append((word,) + bbox + (page_width, page_height))

            elif "page" in element.tag and element.attrib:
                if len(cur_page) > 0:
                    doc.append(cur_page)
                    cur_page = []
                page_width = round(float(element.attrib["width"]))
                page_height = round(float(element.attrib["height"]))

            element.clear()

    if len(cur_page) > 0:
        doc.append(cur_page)
 
    if len(doc) > 0 and skip_first_page(doc[0]):
        doc = doc[1:]
        if remove_ref and ref_page_idx is not None:
            ref_page_idx -= 1

    if remove_ref and ref_page_idx is not None and ref_start_idx_in_page is not None:
        # remove everything that follows references
        doc = doc[: ref_page_idx+1] 
        doc[ref_page_idx] = doc[ref_page_idx][: ref_start_idx_in_page] 

    if any(doc): # no textual contents -> scanned document
        return doc 

    return None


def parse(args):
    fnames = sorted(os.listdir(args.html_dir))
    fnames = fnames[:args.n_docs] if args.n_docs > 0 else fnames 

    if args.resume:
        print("Resuming parsing...")
        fnames = remove_processed_from_id_list(
            fnames, args.parsed_output_log, args.failed_output_log
        )
        if not fnames:
            print(f"All documents in {args.input_file} have already been parsed")
            return

    for html in tqdm(fnames, desc=f"Parsing HTMLs from {args.html_dir}"):
        html_path = os.path.join(args.html_dir, html)
        doc = extract_text_from_tree(
            html_path, do_normalize_bbox=args.do_normalize_bbox, remove_ref=args.remove_ref
        )
        doc_id = html.replace(".html", "")

        if doc is None:
            with open(args.not_parsed_output_log, "a") as f:
                f.write(doc_id + "\n")
        else:
            output_file = os.path.join(
                os.path.join(args.output_dir, doc_id + ".txt")
            )
            with open(output_file, "w", encoding="utf-8") as fw:
                for page_id, p in enumerate(doc):
                    for elem in p:
                        word = elem[0]
                        bbox = elem[1:5]
                        page_width, page_height = elem[5:]

                        bbox_str = (
                            str(bbox[0]) 
                            + "\t" 
                            + str(bbox[1]) 
                            + "\t" 
                            + str(bbox[2]) 
                            + "\t" 
                            + str(bbox[3])
                        )

                        fw.write(
                            word 
                            + "\t" 
                            + bbox_str 
                            + "\t" 
                            + str(page_width) 
                            + "\t" 
                            + str(page_height) 
                            + "\t"
                            + str(page_id+1)
                            + "\n" 
                        )

            with open(args.parsed_output_log, "a") as f:
                f.write(doc_id + "\n")
                    

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--html_dir", 
        type=str,
        required=True,
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        required=True,
    )
    parser.add_argument(
        "--remove_ref",
        action="store_true", 
    )
    parser.add_argument(
        "--n_docs", 
        type=int,
        default=5,
    )
    parser.add_argument(
        "--do_normalize_bbox", 
        action="store_true", 
        help="Normalize bbox coordinates."
    )
    parser.add_argument(
        "--parsed_output_log",
        type=str,
        default="./parsed.log"
    )
    parser.add_argument(
        "--not_parsed_output_log",
        type=str,
        default="./not_parsed_output_log.log"
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

    if os.listdir(args.output_dir) and not args.resume:
        if args.overwrite_output_dir:
            print(f"Overwriting {args.output_dir}")
            shutil.rmtree(args.output_dir)
            os.makedirs(args.output_dir)

            print(f"Overwriting {args.parsed_output_log}")
            os.remove(args.parsed_output_log)

            print(f"Overwriting {args.not_parsed_output_log}")
            os.remove(args.not_parsed_output_log)
        else:
            raise ValueError(
                f"Output directory ({args.output_dir}) already exists and is not empty. Use --overwrite_output_dir to overcome."
            )

    parse(args)