import time
import requests
from pathlib import Path
from pypdf import PdfReader, PdfWriter
from tqdm import tqdm

# Config
API_TOKEN = "YOUR_API_TOKEN_HERE" # Add personal API token
EXTRACTOR_ID = "Y5mPJa5zN7" # Add extractor ID from the website

DELETE_AFTER_SECONDS = 1209600  # 14 days
POLL_INTERVAL = 3  # seconds (rate-limit safe)

BASE_URL = "https://www.handwritingocr.com/api/v3/documents"

HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Accept": "application/json",
}

# Path Setup (script lives in utils/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

PDF_DIR = PROJECT_ROOT / "data" / "tree_inventory_pdfs"
OUTPUT_DIR = PROJECT_ROOT / "data" / "ocr_output"
TEMP_PAGE_DIR = PROJECT_ROOT / "data" / "_temp_pages"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TEMP_PAGE_DIR.mkdir(parents=True, exist_ok=True)

# Helpers
def split_pdf_to_pages(pdf_path: Path, output_dir: Path):
    reader = PdfReader(pdf_path)
    output_dir.mkdir(exist_ok=True)

    page_paths = []

    for i, page in enumerate(reader.pages, start=1):
        writer = PdfWriter()
        writer.add_page(page)

        page_path = output_dir / f"page_{i:04d}.pdf"
        with open(page_path, "wb") as f:
            writer.write(f)

        page_paths.append(page_path)

    return page_paths


def upload_page(page_path: Path) -> str:
    with open(page_path, "rb") as f:
        response = requests.post(
            BASE_URL,
            headers=HEADERS,
            files={"file": f},
            data={
                "action": "extractor",
                "extractor_id": EXTRACTOR_ID,
                "delete_after": DELETE_AFTER_SECONDS,
            },
        )

    response.raise_for_status()
    return response.json()["id"]


def wait_for_processing(doc_id: str):
    while True:
        response = requests.get(f"{BASE_URL}/{doc_id}", headers=HEADERS)

        if response.status_code == 202:
            time.sleep(POLL_INTERVAL)
            continue

        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", POLL_INTERVAL))
            time.sleep(retry_after)
            continue

        response.raise_for_status()

        if response.json()["status"] == "processed":
            return

        time.sleep(POLL_INTERVAL)


def download_json(doc_id: str, output_path: Path):
    response = requests.get(
        f"{BASE_URL}/{doc_id}.json",
        headers=HEADERS,
        stream=True,
    )

    if response.status_code == 429:
        retry_after = int(response.headers.get("Retry-After", POLL_INTERVAL))
        time.sleep(retry_after)
        response = requests.get(
            f"{BASE_URL}/{doc_id}.json",
            headers=HEADERS,
            stream=True,
        )

    response.raise_for_status()

    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)


# Main
def main():
    pdf_files = sorted(
        PDF_DIR.glob("*.pdf"),
        key=lambda p: p.stat().st_size,
    )

    print(f"Found {len(pdf_files)} PDFs")

    for pdf_path in pdf_files:
        pdf_name = pdf_path.stem
        print(f"\n=== {pdf_name} ===")

        pdf_output_dir = OUTPUT_DIR / pdf_name
        pdf_output_dir.mkdir(exist_ok=True)

        temp_pages_dir = TEMP_PAGE_DIR / pdf_name
        temp_pages_dir.mkdir(exist_ok=True)

        page_paths = split_pdf_to_pages(pdf_path, temp_pages_dir)

        with tqdm(page_paths, desc=f"{pdf_name}", unit="page") as pages:
            for page_path in pages:
                page_number = page_path.stem.split("_")[1]
                output_json = pdf_output_dir / f"page_{page_number}.json"

                if output_json.exists():
                    pages.set_postfix_str(f"page {page_number} (skipped)")
                    continue

                pages.set_postfix_str(f"page {page_number}")

                doc_id = upload_page(page_path)
                wait_for_processing(doc_id)
                download_json(doc_id, output_json)

                time.sleep(1)

    print("\nAll PDFs processed.")


if __name__ == "__main__":
    main()