import datetime
import json
import os
import re
import sys
import time
import requests
from bs4 import BeautifulSoup
from pydantic import AnyHttpUrl, BaseModel, Field, ValidationError
from urllib.parse import urljoin, urlparse

BASE_URL = "https://books.toscrape.com"
FIRST_CATALOGUE_URL = f"{BASE_URL}/catalogue/page-1.html"

USER_AGENT = "FlyRankInternship-A9/1.0 (+https://github.com/dfhhgh/scraper)"
TIMEOUT = 10
REQUEST_DELAY = 0.5

MAX_CATALOGUE_PAGES = 3

MAX_RETRIES = 1
RETRY_WAIT = 1.0

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
CACHE_DIR = os.path.join(PROJECT_ROOT, "cache")
BOOK_CACHE_DIR = os.path.join(CACHE_DIR, "books")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
RAW_OUTPUT_FILE = os.path.join(OUTPUT_DIR, "raw_books.json")
BOOKS_OUTPUT_FILE = os.path.join(OUTPUT_DIR, "books.json")
ERRORS_OUTPUT_FILE = os.path.join(OUTPUT_DIR, "errors.json")
RUN_REPORT_FILE = os.path.join(OUTPUT_DIR, "run-report.json")

RATING_MAP = {
    "One": 1,
    "Two": 2,
    "Three": 3,
    "Four": 4,
    "Five": 5,
}


class BookRecord(BaseModel):
    title: str = Field(min_length=1)
    product_url: AnyHttpUrl
    price_gbp: float
    availability: int = Field(ge=0)
    rating: int = Field(ge=1, le=5)
    description: str | None = None
    source_page: AnyHttpUrl
    fetched_at: datetime.datetime


def catalogue_cache_file(page_number):
    return os.path.join(CACHE_DIR, f"catalogue-page-{page_number}.html")


def fetch_html(url, cache_file, metrics):
    display_path = os.path.relpath(cache_file, PROJECT_ROOT)
    if os.path.exists(cache_file):
        with open(cache_file, "r", encoding="utf-8") as f:
            content = f.read()
        metrics["cache_hits"] += 1
        print(f"CACHE HIT {display_path}")
        print(f"response_size={os.path.getsize(cache_file)}")
        return content

    print(f"FETCH {url}")
    attempts = 0
    while True:
        attempts += 1
        try:
            response = requests.get(
                url,
                headers={"User-Agent": USER_AGENT},
                timeout=TIMEOUT,
            )
        except requests.Timeout as exc:
            print(f"TIMEOUT: {url} ({exc})")
            if attempts <= MAX_RETRIES:
                print(f"RETRY {url}")
                time.sleep(RETRY_WAIT)
                continue
            metrics["fetch_attempts"] += attempts
            return None
        except requests.RequestException as exc:
            print(f"FAILED: {url} ({exc})")
            metrics["fetch_attempts"] += attempts
            return None

        if response.status_code == 200:
            break

        if response.status_code >= 500:
            print(f"HTTP {response.status_code} for {url}")
            if attempts <= MAX_RETRIES:
                print(f"RETRY {url}")
                time.sleep(RETRY_WAIT)
                continue
            metrics["fetch_attempts"] += attempts
            return None

        # 403, 404, and other client errors: do not retry
        print(f"FAILED: HTTP {response.status_code} for {url}")
        metrics["fetch_attempts"] += attempts
        return None

    content = response.content
    with open(cache_file, "wb") as f:
        f.write(content)
    metrics["pages_fetched"] += 1
    metrics["fetch_attempts"] += attempts
    print(f"response_size={len(content)}")
    time.sleep(REQUEST_DELAY)
    return content.decode("utf-8")


def get_catalogue_html(url, page_number, metrics):
    cache_file = catalogue_cache_file(page_number)
    content = fetch_html(url, cache_file, metrics)
    if content is None:
        print(f"FAILED: could not fetch catalogue page {url}")
        raise SystemExit(1)
    return content


def find_book_urls(soup, page_url):
    urls = []
    for anchor in soup.select("article.product_pod h3 a"):
        urls.append(urljoin(page_url, anchor["href"]))
    return urls


def find_next_page_url(soup, page_url):
    next_item = soup.find("li", class_="next")
    if next_item is None:
        return None
    anchor = next_item.find("a")
    if anchor is None:
        return None
    return urljoin(page_url, anchor["href"])


def discover_catalogue_pages(metrics):
    catalogue_pages = []
    book_urls = []
    url_to_source = {}

    page_url = FIRST_CATALOGUE_URL
    page_number = 1

    while page_number <= MAX_CATALOGUE_PAGES:
        html = get_catalogue_html(page_url, page_number, metrics)
        soup = BeautifulSoup(html, "html.parser")

        catalogue_pages.append(page_url)
        found = find_book_urls(soup, page_url)
        for url in found:
            url_to_source[url] = page_url
        book_urls.extend(found)

        if page_number == MAX_CATALOGUE_PAGES:
            break

        next_url = find_next_page_url(soup, page_url)
        if next_url is None:
            print("FAILED: no next page link found")
            raise SystemExit(1)

        page_url = next_url
        page_number += 1

    unique_urls = list(dict.fromkeys(book_urls))

    print(f"catalogue_pages={len(catalogue_pages)}")
    print(f"discovered={len(book_urls)}")
    print(f"unique_urls={len(unique_urls)}")

    return unique_urls, url_to_source


def book_cache_file(url):
    path = urlparse(url).path.lstrip("/")
    filename = path.replace("/", "-")
    return os.path.join(BOOK_CACHE_DIR, filename)


def get_book_html(url, metrics):
    cache_file = book_cache_file(url)
    return fetch_html(url, cache_file, metrics)


def extract_book_details(soup, product_url, source_page, fetched_at):
    title_node = soup.select_one("div.product_main h1")
    title = title_node.get_text(strip=True) if title_node else None

    price_node = soup.select_one("p.price_color")
    price_text = price_node.get_text(strip=True) if price_node else None

    availability_node = soup.select_one("p.instock.availability")
    availability_text = (
        availability_node.get_text(strip=True) if availability_node else None
    )

    rating_text = None
    rating_node = soup.select_one("p.star-rating")
    if rating_node is not None:
        classes = [c for c in rating_node.get("class", []) if c != "star-rating"]
        if classes:
            rating_text = classes[0]

    description = None
    description_header = soup.select_one("#product_description")
    if description_header is not None:
        paragraph = description_header.find_next_sibling("p")
        if paragraph is not None:
            description = paragraph.get_text(strip=True)

    return {
        "title": title,
        "product_url": product_url,
        "price_text": price_text,
        "availability_text": availability_text,
        "rating_text": rating_text,
        "description": description,
        "source_page": source_page,
        "fetched_at": fetched_at,
    }


def normalize_record(raw):
    title = raw.get("title")
    if not title or not title.strip():
        raise ValueError("title: missing or empty")

    product_url = raw.get("product_url")
    if not product_url:
        raise ValueError("product_url: missing")

    source_page = raw.get("source_page")
    if not source_page:
        raise ValueError("source_page: missing")

    fetched_at = raw.get("fetched_at")
    if not fetched_at:
        raise ValueError("fetched_at: missing")

    price_text = raw.get("price_text")
    price_match = re.search(r"\d+(?:\.\d+)?", price_text or "")
    if not price_match:
        raise ValueError(f"price_gbp: could not parse price from {price_text!r}")
    price_gbp = float(price_match.group())

    rating_text = raw.get("rating_text")
    if rating_text not in RATING_MAP:
        raise ValueError(f"rating: unknown rating text {rating_text!r}")
    rating = RATING_MAP[rating_text]

    availability_text = raw.get("availability_text")
    availability_match = re.search(r"\d+", availability_text or "")
    if not availability_match:
        raise ValueError(
            f"availability: could not parse availability from {availability_text!r}"
        )
    availability = int(availability_match.group())

    return {
        "title": title.strip(),
        "product_url": product_url,
        "price_gbp": price_gbp,
        "availability": availability,
        "rating": rating,
        "description": raw.get("description"),
        "source_page": source_page,
        "fetched_at": fetched_at,
    }


def normalize_and_validate():
    with open(RAW_OUTPUT_FILE, "r", encoding="utf-8") as f:
        raw_records = json.load(f)

    valid_records = []
    invalid_records = []

    for raw in raw_records:
        try:
            normalized = normalize_record(raw)
            model = BookRecord(**normalized)
        except (ValueError, ValidationError) as exc:
            if isinstance(exc, ValidationError):
                errors = [
                    f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
                    for error in exc.errors()
                ]
            else:
                errors = [str(exc)]
            invalid_records.append({"record": raw, "errors": errors})
            continue

        record_out = model.model_dump(mode="json")
        record_out["fetched_at"] = model.fetched_at.isoformat()
        valid_records.append(record_out)

    with open(BOOKS_OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(valid_records, f, ensure_ascii=False, indent=2)
    with open(ERRORS_OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(invalid_records, f, ensure_ascii=False, indent=2)

    print(f"raw_records={len(raw_records)}")
    print(f"valid={len(valid_records)}")
    print(f"invalid={len(invalid_records)}")

    return len(valid_records), len(invalid_records)


def main():
    test_failure = "--test-failure" in sys.argv
    started_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    start_time = time.time()

    os.makedirs(BOOK_CACHE_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    metrics = {
        "pages_fetched": 0,
        "cache_hits": 0,
        "fetch_attempts": 0,
    }

    unique_urls, url_to_source = discover_catalogue_pages(metrics)

    if test_failure:
        fake_url = f"{BASE_URL}/catalogue/this-book-does-not-exist_99999/index.html"
        print(f"TEST MODE: appending fake URL {fake_url}")
        unique_urls.append(fake_url)

    records = []
    processed = 0
    failed_pages = 0

    for url in unique_urls:
        processed += 1
        html = get_book_html(url, metrics)
        if html is None:
            failed_pages += 1
            print(f"FAILED PAGE: {url}")
            continue

        fetched_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        soup = BeautifulSoup(html, "html.parser")
        records.append(
            extract_book_details(soup, url, url_to_source[url], fetched_at)
        )

    with open(RAW_OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    print(f"discovered={len(unique_urls)}")
    print(f"processed={processed}")
    print(f"extracted={len(records)}")
    print(f"failed={failed_pages}")

    valid_count, invalid_count = normalize_and_validate()

    duration = time.time() - start_time
    report = {
        "started_at": started_at,
        "duration_seconds": round(duration, 3),
        "pages_fetched": metrics["pages_fetched"],
        "cache_hits": metrics["cache_hits"],
        "valid_records": valid_count,
        "invalid_records": invalid_count,
        "failed_pages": failed_pages,
    }
    with open(RUN_REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"run-report written to output/run-report.json")


if __name__ == "__main__":
    main()