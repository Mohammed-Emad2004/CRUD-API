# The Polite Scraper

A small, polite scraping pipeline for the [Books to Scrape](https://books.toscrape.com/)
practice sandbox. It downloads the first 3 catalogue pages, discovers exactly 60
unique books, extracts and validates their data, and writes clean JSON outputs —
all while keeping the request rate low and caching during development.

### Results

| Metric                     | Value                        |
| -------------------------- | ---------------------------- |
| Catalogue pages            | 3                            |
| Book URLs discovered       | 60                           |
| Unique URLs                | 60                           |
| Valid records              | 60                           |
| Invalid records            | 0                            |
| Retry policy               | timeout / 5xx, one retry     |
| Failure isolation          | yes                          |
| Local caching              | yes                          |
| Browser automation         | no                           |

---

## Table of Contents

- [Overview](#overview)
- [Target Classification](#target-classification)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Pipeline](#pipeline)
- [Record Schema](#record-schema)
- [Politeness Rules](#politeness-rules)
- [Failure Handling](#failure-handling)
- [Output Files](#output-files)
- [Run Report](#run-report)
- [Verification](#verification)
- [Design Decisions](#design-decisions)
- [Limitations](#limitations)
- [Ethics](#ethics)
- [Project Structure](#project-structure)

---

## Overview

This project is a focused, ethical exercise in building a repeatable scraping
workflow. It is **not** a production crawler.

The pipeline:

- downloads the first 3 catalogue pages from Books to Scrape
- discovers exactly 60 unique book URLs
- visits each book's detail page and extracts raw fields
- normalizes price, rating, and availability
- validates every record with Pydantic
- writes validated records to `output/books.json` and invalid ones to `output/errors.json`
- isolates broken pages so one failure never kills the run
- retries only timeout / 5xx errors exactly once
- writes a run report to `output/run-report.json`

---

## Target Classification

- **Target site:** Books to Scrape
- **Base URL:** https://books.toscrape.com/

### Why this target is appropriate

Books to Scrape is a public practice sandbox specifically intended for learning
and testing web scraping. It is designed as a safe, ethical target with no risk
of harming a real website or violating any terms of service.

### Scope

- ONLY the first 3 catalogue pages of the site.
- Expected dataset: 60 books (20 per catalogue page).

### Data collected

Book information from those 3 catalogue pages and their book detail pages,
including title, price, availability, rating, and description.

### robots.txt check (from Stage 0)

**URL checked:** https://books.toscrape.com/robots.txt

**Result:** no robots file found

The site returned a 404 status, indicating no robots.txt file is present.
A missing robots.txt is not interpreted as permission; the scope remains
limited to the first 3 catalogue pages as specified.

### Disclaimer

This code is intended only for this assignment's approved practice sandbox.
I will not reuse this code on another site without checking its rules and terms first.

---

## Architecture

The pipeline is separated into distinct stages so each concern can be tested and
reasoned about independently:

```
Catalogue pages
      ↓
Book URL discovery
      ↓
Cached HTTP fetching
      ↓
Raw extraction
      ↓
Normalization
      ↓
Pydantic validation
      ↓
books.json / errors.json
      ↓
run-report.json
```

Separating the stages means that fetching, extraction, normalization, and
validation never get tangled together. A change in one area (for example, a new
normalization rule) does not affect the HTTP or caching behavior, and a failure
at any step can be reported instead of aborting the whole run.

---

## Quick Start

The whole setup should take under five minutes.

```bash
git clone https://github.com/dfhhgh/scraper.git
cd scraper
python -m venv .venv
```

Activate the virtual environment:

- **Windows (PowerShell):**
  ```powershell
  .venv\Scripts\Activate.ps1
  ```
- **macOS / Linux:**
  ```bash
  source .venv/bin/activate
  ```

Install dependencies and run:

```bash
pip install -r requirements.txt
python src/main.py
```

Expected high-level output:

```
discovered=60
processed=60
extracted=60
failed=0
raw_records=60
valid=60
invalid=0
```

On the first run the scraper makes the real HTTP requests (a few catalogue
pages, then 60 book pages with a 0.5-second delay between them). On later runs
it reads everything from the local cache and performs no network requests.
Exact runtime varies with network speed.

---

## Pipeline

### Stage 1 — HTTP fetching & caching

- Fetches `https://books.toscrape.com/catalogue/page-1.html`.
- Sends an identifying User-Agent and uses an explicit 10-second timeout.
- Only HTTP 200 is accepted; anything else fails cleanly with a non-zero exit.
- Saves the first response to `cache/catalogue-page-1.html`; later runs reuse
  the cache and make no HTTP request.

### Stage 2 — Find all three catalogue pages

- Starts from the cached first catalogue page.
- Follows the site's "next" navigation link (never hard-codes page 2 / page 3).
- Resolves relative URLs with `urllib.parse.urljoin()`.
- Discovers book URLs from all three catalogue pages and deduplicates them.

Checkpoint:

```
catalogue_pages=3
discovered=60
unique_urls=60
```

### Stage 3 — Extract book details

- Fetches all 60 unique book detail pages sequentially.
- Uses at least a 0.5-second delay between real HTTP requests; cache hits skip
  the delay.
- Caches every book page under `cache/books/`.
- Extracts eight raw fields per book: `title`, `product_url`, `price_text`,
  `availability_text`, `rating_text`, `description`, `source_page`, `fetched_at`.
- Raw text is preserved (`price_text` `"£51.77"`, `rating_text` `"Three"`,
  `availability_text` `"In stock (22 available)"`).
- A missing description is stored as `null`, never fabricated.
- Failed pages are reported and skipped without creating fake records.
- Writes the intermediate `output/raw_books.json`.

Checkpoint:

```
discovered=60
processed=60
extracted=60
failed=0
```

### Stage 4 — Normalize & validate

- Consumes `output/raw_books.json`.
- Normalizes price, rating, and availability, then validates every record with
  a Pydantic `BookRecord` model (validation happens **after** normalization).
- Valid records are written to `output/books.json`; invalid records to
  `output/errors.json` with diagnostic messages.
- Output is deterministic (order preserved) and idempotent (rebuilt each run,
  never appended).

Checkpoint:

```
raw_records=60
valid=60
invalid=0
```

### Stage 5 — Survive failures, report the run

- Every book page is processed independently; a broken page is logged and
  skipped without crashing the run.
- Timeout and HTTP 5xx receive exactly one retry after a brief wait.
- HTTP 403, 404, and other client errors are never retried.
- Every run writes `output/run-report.json` with honest metrics.
- A deliberate failure test (`python src/main.py --test-failure`) appends one
  fake URL for that run only; it fails, the 60 real books still produce valid
  records, and the report records `failed_pages: 1`.

Checkpoint (normal run):

```
discovered=60
processed=60
extracted=60
failed=0
raw_records=60
valid=60
invalid=0
```

---

## Record Schema

Every validated record in `output/books.json` follows this schema:

| Field          | Type           | Description                                        |
| -------------- | -------------- | -------------------------------------------------- |
| `title`        | string         | Book title                                          |
| `product_url`  | URL            | Absolute URL of the book's detail page              |
| `price_gbp`    | float          | Price in British pounds                             |
| `availability` | integer        | Number of units in stock                            |
| `rating`       | integer 1–5    | Star rating                                         |
| `description`  | string \| null | Book description (null when missing)                |
| `source_page`  | URL            | Catalogue page the book was discovered on           |
| `fetched_at`   | datetime       | ISO-8601 UTC timestamp of the fetch                 |

### Normalization examples

Fields are normalized first, then validated:

- `price_text` `"£51.77"` → `price_gbp` `51.77`
- `rating_text` `"Three"` → `rating` `3`
- `availability_text` `"In stock (22 available)"` → `availability` `22`

Invalid records never appear in `books.json`; they are written to
`output/errors.json` together with the diagnostic errors.

---

## Politeness Rules

The scraper is deliberately polite to the target site. The rules below match
the actual implementation.

- **User-Agent:** every request identifies the scraper:

  ```
  FlyRankInternship-A9/1.0 (+https://github.com/dfhhgh/scraper)
  ```

- **Timeout:** every request has an explicit 10-second timeout.
- **Delay:** at least 0.5 seconds between real HTTP requests.
- **Cache:** cached pages cause no HTTP request, and therefore no delay.
- **Status code:** HTTP 200 is required before a response is parsed.
- **Development caching:** all fetched pages are stored locally so repeated
  development runs reuse the cache instead of hitting the site again.
- **Retries:** only timeout and HTTP 5xx receive one retry; HTTP 403 and 404
  are never retried.

---

## Failure Handling

Each book page is processed independently. A single broken page:

- is logged
- is skipped
- does not crash the complete run
- does not remove the other valid records

Two distinct scenarios are exercised:

| Scenario                | `failed_pages` |
| ----------------------- | -------------- |
| Normal run              | 0              |
| Deliberate failure test | 1              |

The deliberate failure test (`python src/main.py --test-failure`) adds one
fake/nonexistent book URL **in memory for that run only**. It fails with HTTP
404, the 60 real books still produce valid records, and the report records
`failed_pages: 1`. The fake URL is never part of the production URL list, and
the real website is not hammered to test failures.

---

## Output Files

| File                        | Purpose                                        |
| --------------------------- | ---------------------------------------------- |
| `output/books.json`         | Validated records                              |
| `output/errors.json`        | Invalid records + diagnostics                  |
| `output/raw_books.json`     | Intermediate raw records                       |
| `output/run-report.json`    | Run metrics                                    |
| `output/sample-books.json`  | Committed representative sample                |

Only `output/sample-books.json` is committed to the repository. All other
generated files and the `cache/` directory are git-ignored.

### Sample output

`output/sample-books.json` contains 2 representative records. One record looks
like this (description abbreviated here for readability):

```json
{
  "title": "A Light in the Attic",
  "product_url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
  "price_gbp": 51.77,
  "availability": 22,
  "rating": 3,
  "description": "It's hard to imagine a world without A Light in the Attic. ...",
  "source_page": "https://books.toscrape.com/catalogue/page-1.html",
  "fetched_at": "2026-08-19T12:49:23.604616+00:00"
}
```

---

## Run Report

Every run writes `output/run-report.json`:

| Field              | Meaning                                              |
| ------------------ | ---------------------------------------------------- |
| `started_at`       | ISO-8601 UTC start time                              |
| `duration_seconds` | Wall-clock duration of the run                       |
| `pages_fetched`    | Successful HTTP fetches (cache hits excluded)        |
| `cache_hits`       | Pages served from the local cache                    |
| `valid_records`    | Records written to `books.json`                      |
| `invalid_records`  | Records written to `errors.json`                     |
| `failed_pages`     | Pages that ultimately failed to fetch                |

Real example from an actual normal run (all pages already cached):

```json
{
  "started_at": "2026-08-19T12:49:23.561616+00:00",
  "duration_seconds": 0.329,
  "pages_fetched": 0,
  "cache_hits": 63,
  "valid_records": 60,
  "invalid_records": 0,
  "failed_pages": 0
}
```

`pages_fetched: 0` here is honest: this particular run used the fully warm
local cache (3 catalogue pages + 60 book pages = 63 cache hits) and made no
network requests.

---

## Verification

The results below were observed on a real run of the pipeline.

- `catalogue_pages = 3`
- `discovered = 60`
- `unique_urls = 60`
- `valid records = 60`
- `invalid records = 0`
- Normal run: `failed_pages = 0`
- Deliberate failure test: `failed_pages = 1`, while `books.json` keeps exactly
  60 valid records
- A second run is idempotent and uses the cache (no network requests,
  `cache_hits = 63`)

To verify for yourself:

```bash
python src/main.py                 # normal run: 60 valid, 0 invalid, 0 failed
python src/main.py --test-failure  # deliberate failure test: failed_pages=1
```

---

## Design Decisions

### Why requests + BeautifulSoup?

The target serves the required data as static HTML. A plain HTTP client plus an
HTML parser is the simplest tool that works; no browser runtime is needed.

### Why Pydantic?

It enforces the final record schema and rejects malformed data at the boundary,
so bad records are caught explicitly and written to `errors.json`.

### Why sequential requests?

The assignment prioritizes politeness and a small, controlled workload.
Sequential fetching with a delay keeps the request rate deliberately low.

### Why cache?

To avoid repeatedly requesting the target during development. Every fetched
page is stored locally and reused on later runs.

### Why no browser?

The required data is already present in server-rendered HTML. A browser would
add unnecessary cost and complexity. Browser automation is only appropriate
when data is rendered after JavaScript execution, which is not the case for
the core Books to Scrape task.

---

## Limitations

These are intentional scope decisions, not bugs:

- Scope is limited to the first 3 catalogue pages.
- Designed for the assignment's practice sandbox (Books to Scrape).
- Not a general-purpose production crawler.
- No JavaScript / browser automation in the core pipeline.
- No concurrency.
- No large-scale crawling.
- No authentication bypassing or anti-bot circumvention.

---

## Ethics

Scraping responsibly means respecting the target and the data:

- Prefer an official API when one exists.
- Never bypass authentication, paywalls, rate limits, or blocks.
- Collect only the data actually needed.
- Respect `robots.txt` and the site's terms and rules.
- Identify the scraper with a meaningful User-Agent.
- Keep request rates low.
- Cache during development instead of repeatedly requesting the site.

This project follows these principles: it targets a public practice sandbox,
identifies itself, uses a low request rate, caches aggressively, and never
touches more than the first 3 catalogue pages and their 60 book detail pages.

This code is intended only for this assignment's approved practice sandbox.
I will not reuse this code on another site without checking its rules and terms first.

---

## GitHub / Reproducibility

A reviewer can clone the repository, install the dependencies, run the scraper,
and inspect the generated JSON outputs without needing external services, API
keys, or paid infrastructure. Everything runs locally with Python and three
small dependencies.

---

## Project Structure

### Tracked in the repository

```
scraper/
├── README.md
├── .gitignore
├── requirements.txt
├── src/
│   └── main.py
└── output/
    └── sample-books.json      # committed sample evidence (2 records)
```

### Generated at runtime (git-ignored)

```
cache/                         # catalogue + book HTML cache
.venv/                         # virtual environment
output/books.json              # validated records
output/errors.json             # invalid records + diagnostics
output/raw_books.json          # intermediate raw records
output/run-report.json         # run metrics
```

The `cache/` directory and all generated output files are ignored by Git and
are not committed. Only `output/sample-books.json` is committed as
representative evidence.