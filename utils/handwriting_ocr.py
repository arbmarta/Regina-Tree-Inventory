import time
import json
import os
from dotenv import load_dotenv
load_dotenv()

import requests
from pathlib import Path
from pypdf import PdfReader, PdfWriter

# CONFIG
API_TOKEN = os.environ["HWOCR_API_TOKEN"]
EXTRACTOR_ID = "Y5mPJa5zN7"

BATCH_SIZE = 2
POLL_INTERVAL = 3
DELETE_AFTER_SECONDS = 1209600  # 14 days

BASE_URL = "https://www.handwritingocr.com/api/v3/documents"

HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Accept": "application/json",
}

# PATHS
PROJECT_ROOT = Path(__file__).resolve().parent.parent

MERGED_PDF = PROJECT_ROOT / "data" / "tree_inventories_merged.pdf"
OUTPUT_DIR = PROJECT_ROOT / "data" / "ocr_output"
TEMP_DIR = PROJECT_ROOT / "data" / "_temp_pages"
LOG_PATH = PROJECT_ROOT / "data" / "processing_log.json"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# LOG HELPERS (atomic write)
def load_log():
    if LOG_PATH.exists():
        return json.loads(LOG_PATH.read_text())
    return {}

def save_log(log):
    tmp = LOG_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(log, indent=2))
    tmp.replace(LOG_PATH)

# RETRY HELPER
def retry_request(fn, retries=3, delay=3):
    for attempt in range(retries):
        try:
            return fn()
        except requests.RequestException:
            if attempt == retries - 1:
                raise
            time.sleep(delay)

# PDF HELPERS
def extract_page(reader: PdfReader, page_number: int) -> Path:
    writer = PdfWriter()
    writer.add_page(reader.pages[page_number - 1])

    out_path = TEMP_DIR / f"page_{page_number:06d}.pdf"
    with open(out_path, "wb") as f:
        writer.write(f)

    return out_path

# API HELPERS
def upload_page(page_path: Path) -> str:
    with open(page_path, "rb") as f:
        r = requests.post(
            BASE_URL,
            headers=HEADERS,
            files={"file": f},
            data={
                "action": "extractor",
                "extractor_id": EXTRACTOR_ID,
                "delete_after": DELETE_AFTER_SECONDS,
            },
        )
    r.raise_for_status()
    return r.json()["id"]

def wait_for_processing(doc_id: str, max_attempts=120):
    attempts = 0
    while attempts < max_attempts:
        r = requests.get(f"{BASE_URL}/{doc_id}", headers=HEADERS)

        if r.status_code == 202:
            time.sleep(POLL_INTERVAL)
            attempts += 1
            continue

        if r.status_code == 429:
            retry_after = int(r.headers.get("Retry-After", POLL_INTERVAL))
            time.sleep(retry_after)
            continue

        r.raise_for_status()

        if r.json().get("status") == "processed":
            return

        time.sleep(POLL_INTERVAL)
        attempts += 1

    raise TimeoutError(f"OCR timed out for doc_id={doc_id}")

def download_json(doc_id: str, page_number: int, max_attempts=20):
    out_file = OUTPUT_DIR / f"page_{page_number:06d}.json"
    attempts = 0

    while attempts < max_attempts:
        r = requests.get(f"{BASE_URL}/{doc_id}.json", headers=HEADERS)

        if r.status_code == 429:
            retry_after = int(r.headers.get("Retry-After", POLL_INTERVAL))
            time.sleep(retry_after)
            attempts += 1
            continue

        r.raise_for_status()
        out_file.write_bytes(r.content)
        return

    raise TimeoutError(f"Download timed out for doc_id={doc_id}")

# MAIN PIPELINE (LOOPS UNTIL DONE)
def main():
    log = load_log()
    reader = PdfReader(MERGED_PDF)
    total_pages = len(reader.pages)

    print(f"Total pages: {total_pages}")

    while True:
        # Determine next batch
        unprocessed = [
            i for i in range(1, total_pages + 1)
            if log.get(str(i), {}).get("status") != "processed"
        ]

        if not unprocessed:
            print("All pages processed.")
            return

        batch = unprocessed[:BATCH_SIZE]
        print(f"\nProcessing batch: pages {batch[0]} → {batch[-1]}")

        # -----------------------------
        # PHASE 1: UPLOAD
        # -----------------------------
        for page_number in batch:
            if log.get(str(page_number), {}).get("status") == "submitted":
                continue

            print(f"Uploading page {page_number}")
            page_pdf = extract_page(reader, page_number)

            doc_id = retry_request(lambda p=page_pdf: upload_page(p))

            log[str(page_number)] = {
                "doc_id": doc_id,
                "status": "submitted"
            }
            save_log(log)

            page_pdf.unlink()
            time.sleep(1)

        # -----------------------------
        # PHASE 2: DOWNLOAD
        # -----------------------------
        for page_number in batch:
            entry = log.get(str(page_number))
            if not entry or entry["status"] != "submitted":
                continue

            doc_id = entry["doc_id"]
            print(f"Downloading page {page_number}")

            wait_for_processing(doc_id)
            download_json(doc_id, page_number)

            entry["status"] = "processed"
            save_log(log)

            time.sleep(1)

if __name__ == "__main__":
    main()
