import os
from pypdf import PdfReader, PdfWriter

MAX_SIZE_MB = 75
MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024


def split_pdf_in_half(pdf_path):
    reader = PdfReader(pdf_path)
    total_pages = len(reader.pages)
    midpoint = total_pages // 2

    base, ext = os.path.splitext(pdf_path)

    writer_a = PdfWriter()
    writer_b = PdfWriter()

    for i in range(midpoint):
        writer_a.add_page(reader.pages[i])

    for i in range(midpoint, total_pages):
        writer_b.add_page(reader.pages[i])

    with open(f"{base}_A{ext}", "wb") as f:
        writer_a.write(f)

    with open(f"{base}_B{ext}", "wb") as f:
        writer_b.write(f)

    print(f"Split: {pdf_path} → {base}_A{ext}, {base}_B{ext}")


def process_current_folder():
    for filename in os.listdir("."):
        if not filename.lower().endswith(".pdf"):
            continue

        # Skip already-split files
        if filename.endswith("_A.pdf") or filename.endswith("_B.pdf"):
            continue

        file_size = os.path.getsize(filename)

        if file_size > MAX_SIZE_BYTES:
            split_pdf_in_half(filename)


if __name__ == "__main__":
    process_current_folder()
