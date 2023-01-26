import scrapy 
import re 
from scrapy.crawler import CrawlerProcess
import argparse
import os 
from src.utils import del_file_if_exists
import json
import random
import langdetect
from langdetect import DetectorFactory

DetectorFactory.seed = 0

class KoreaScienceSpider(scrapy.Spider):
    name = "koreascience_spider"
    custom_settings = {
        'DOWNLOAD_DELAY': 3, # amount of time (in secs) waiting before downloading consecutive pages
        'FEED_EXPORT_ENCODING': 'utf-8',
        'LOG_LEVEL': 'INFO',
        'USER_AGENTS': [
            ('Mozilla/5.0 (X11; Linux x86_64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/57.0.2987.110 '
            'Safari/537.36'),  # chrome
            ('Mozilla/5.0 (X11; Linux x86_64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/61.0.3163.79 '
            'Safari/537.36'),  # chrome
            ('Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:55.0) '
            'Gecko/20100101 '
            'Firefox/55.0')  # firefox
        ]
    }

    def start_requests(self):
        ids_crawled = None 
        if self.resume_crawl:
            ids_crawled = []
            with open(self.output_file) as f:
                for line in f:
                    item = json.loads(line)
                    ids_crawled.append(item["id"])
            print("Resuming crawl from {}... Skipping {} publications".format(
                self.start_url,
                len(ids_crawled),
            ))

        yield scrapy.Request(self.start_url, meta={'ids_crawled': ids_crawled}, headers={"User-Agent": random.choice(self.custom_settings['USER_AGENTS'])})
 

    def parse(self, response):
        ITEM_SELECTOR = 'div#search-result > section > article.srched-box'
        PAGE_COUNTER_SELECTOR = './/nav[@aria-label="Page Navigation"]/ul/li[@class="list-inline-item float-right "]/span/text()'
        
        page_counter = response.xpath(PAGE_COUNTER_SELECTOR).extract_first()
        if page_counter is not None:
            matches = re.search(
                r"(\d+|[0-9]{1,3},[0-9]{3}) \/ (\d+|[0-9]{1,3},[0-9]{3}) pages", 
                page_counter
            )
            current_page = int(matches.group(1).replace(",", ""))
            total_num_pages = int(matches.group(2).replace(",", ""))
            stop_page = self.stop_page if self.stop_page > 0 else total_num_pages
        else: # Last page 
            current_page = re.search(r"&pageNo=(\d+)", response.url).group(1)
            total_num_pages = current_page
            stop_page = self.stop_page if self.stop_page > 0 else total_num_pages

        print("Processing page {}/{} (stopping at page {})".format(current_page, total_num_pages, stop_page))
        print("\t" + response.url)

        for publication in response.css(ITEM_SELECTOR):
            DETAILS_URL_SELECTOR = './h3/a/@href'
            JOURNAL_SELECTOR = './/div[@class="d-lg-flex justify-content-between align-items-center"]/ul/li[2]/ul/li/text()'
            PREVIEW_ABSTRACT_SELECTOR = './/div[@class="d-lg-flex justify-content-between align-items-center"]/ul/li[3]/p/text()'

            details_url = publication.xpath(DETAILS_URL_SELECTOR).extract_first()
            pub_id = re.search(
                '\/article\/(([A-Za-z_0-9.-]+).*)\.page',
                details_url
            ).group(1)

            journal = publication.xpath(JOURNAL_SELECTOR).extract_first().strip()

            item = {"id": pub_id, "journal": journal}

            if (
                response.meta['ids_crawled'] is not None 
                and item['id'] in response.meta['ids_crawled']
            ):
                print("Skipping ", item['id'])
                continue 

            preview_abstract = publication.xpath(PREVIEW_ABSTRACT_SELECTOR).extract_first().strip()
            if len(preview_abstract) == 0:
                continue 

            yield scrapy.Request(
                response.urljoin(details_url),
                callback=self.parse_article_page,
                meta={'item': item},
                headers={"User-Agent": random.choice(self.custom_settings['USER_AGENTS'])}
            )

        
        
        if current_page < stop_page:
            next_url = response.url.replace(
                f"&pageNo={current_page}", f"&pageNo={current_page + 1}"
            )
            yield scrapy.Request(
                response.urljoin(next_url),
                callback=self.parse,
                meta=response.meta,
                headers={"User-Agent": random.choice(self.custom_settings['USER_AGENTS'])}
            )
    
    def parse_article_page(self, response):
        item = response.meta['item']

        PDF_URL_SELECTOR = './/div[@class="contents-table"]/a/@href'
        ABSTRACTS_SELECTOR = './/div[@class="article-box" and h4[contains(text(), "Abstract")]]/p'
        KEYWORDS_SELECTOR = './/div[@class="article-box" and h4[contains(text(), "Keywords")]]/ul/li/a/text()'
        PUBLICATION_DATE = './/ul[@class="list-inline"]/li[@class="list-inline-item" and contains(text(), "Published")]/text()'
        DOI_SELECTOR = './/a[@class="btn btn-link pl0"]/@href'

        pdf_url = response.xpath(PDF_URL_SELECTOR).extract_first()
        if pdf_url is not None:
            item["pdf_url"] = "http://koreascience.or.kr" + pdf_url 
        else:
            item["pdf_url"] = "" # todo: standardize: either None or empty string

        all_abstracts = response.xpath(ABSTRACTS_SELECTOR)

        for p_abstract in all_abstracts:
            abstract_list = p_abstract.xpath("./text()").extract()
            abstract_list = [sub_abstract.strip() for sub_abstract in abstract_list]
            abstract = " ".join(abstract_list)
            try:
                lang_abstract = langdetect.detect(abstract)
                item["abstract_" + lang_abstract] = abstract
            except langdetect.lang_detect_exception.LangDetectException:
                print(f"Unable to detect language for {abstract} ({response.url})")

        keywords = response.xpath(KEYWORDS_SELECTOR).extract()
        if len(keywords) > 0:
            item["keywords"] = keywords
        else:
            item["keywords"] = None 

        publication_date = response.xpath(PUBLICATION_DATE).extract_first()
        if publication_date is not None:
            publication_date = publication_date.replace("Published : ", "")
        
        item["publication_date"] = publication_date
        item["doi"] = response.xpath(DOI_SELECTOR).extract_first()

        return item


def crawl_koreascience(args):
    process = CrawlerProcess(settings={
        "FEEDS": {
            args.output_file: {"format": "jsonlines"}
        }
    })

    process.crawl(
        KoreaScienceSpider, 
        start_url=args.start_url, 
        stop_page=args.stop_page,
        resume_crawl=args.resume_crawl,
        output_file=args.output_file
    )
    process.start()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--start_url",
        type=str,
        required=True,
    )
    parser.add_argument(
        "--output_file",
        type=str,
        required=True,
    )
    parser.add_argument(
        "--stop_page",
        type=int,
        default=-1
    )
    parser.add_argument(
        "--overwrite_output", 
        action="store_true", 
        help="Overwrite the output file."
    )
    parser.add_argument(
        "--resume_crawl", 
        action="store_true", 
    )

    args = parser.parse_args()

    if args.resume_crawl and args.overwrite_output:
        raise ValueError(
            f"Cannot use --resume and --overwrite_output at the same time."
        )

    if os.path.exists(args.output_file) and not args.resume_crawl:
        if args.overwrite_output:
            del_file_if_exists(args.output_file)
        else:
            raise ValueError(
                f"Output file ({args.output_file}) already exists and is not empty. Use --overwrite_output to overcome."
            )

    crawl_koreascience(args)