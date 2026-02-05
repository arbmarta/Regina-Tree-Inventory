from pathlib import Path
from pypdf import PdfReader, PdfWriter

# ---- CONFIG ----
pdf_dir = Path(r"tree_inventory_pdfs")
MERGED_NAME = "tree_inventory_merged.pdf"

# OCR pricing models
def cost_option_1(pages):
    return ((pages + 99) // 100) * 15

def cost_option_2(pages):
    return 19 if pages <= 250 else 19 + (pages - 250) * 0.06

def cost_option_3(pages):
    return 49 if pages <= 1000 else 49 + (pages - 1000) * 0.05

def cost_option_4(pages):
    return 399 if pages <= 10_000 else 399 + (pages - 10_000) * 0.04

# ---- TABLE HEADER ----
header = f"{'File':50} {'Pages':>7} {'Size (MB)':>10}"
print(header)
print("-" * len(header))

total_pages = 0
total_size_mb = 0.0

# ---- COLLECT INPUT PDFs (EXCLUDING MERGED FILE) ----
pdf_files = sorted(
    pdf for pdf in pdf_dir.glob("*.pdf")
    if pdf.name != MERGED_NAME
)

# ---- PER-FILE ROWS ----
for pdf in pdf_files:
    reader = PdfReader(pdf)
    pages = len(reader.pages)
    size_mb = pdf.stat().st_size / (1024 * 1024)

    total_pages += pages
    total_size_mb += size_mb

    print(f"{pdf.name:50} {pages:7d} {size_mb:10.2f}")

# ---- TOTAL ROW ----
print("-" * len(header))
print(f"{'TOTAL':50} {total_pages:7d} {total_size_mb:10.2f}")

# ---- COST ANALYSIS ----
print("\nOCR COST ANALYSIS")
print("----------------------")

costs = {
    "Option 1 (£15 per 100 pages)": cost_option_1(total_pages),
    "Option 2 (£19/250 + 6p/page)": cost_option_2(total_pages),
    "Option 3 (£49/1000 + 5p/page)": cost_option_3(total_pages),
    "Option 4 (£399/10000 + 4p/page)": cost_option_4(total_pages),
}

for name, cost in costs.items():
    print(f"{name:35} £{cost:,.2f}")

best_option = min(costs, key=costs.get)

print("\nCHEAPEST OPTION")
print("----------------------")
print(f"{best_option}")
print(f"Cost: £{costs[best_option]:,.2f}")

# ---- MERGE ALL PDFs (SAFE OVERWRITE) ----
print("\nMerging PDFs...")
writer = PdfWriter()

for pdf in pdf_files:
    reader = PdfReader(pdf)
    for page in reader.pages:
        writer.add_page(page)

output_path = pdf_dir / MERGED_NAME

with open(output_path, "wb") as f:
    writer.write(f)

print(f"Merged PDF replaced: {output_path}")
