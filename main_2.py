import json
import re
import csv
from collections import Counter
from pathlib import Path

# ---- LOAD JSON ----
json_path = Path("zaran-zech-place-0c8ec1ee77d5.json")

with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# ---- DATA STRUCTURES ----
species_counter = Counter()
street_counter = Counter()

total_rows = 0          # all inventory positions
total_trees = 0         # planted trees ONLY
blank_spaces = 0        # unplanted placeholders

tree_rows = []

current_street = None
current_street_number = None

# ---- HELPERS ----
def normalize_species(name):
    if not name:
        return None
    name = re.sub(r"[^\w\s\-']", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name.title() if name else None

INVALID_SPECIES = {"driveway", "stump", "vacant"}

# ---- PARSE TRANSCRIPTS ----
for page in data["results"]:
    text = page["transcript"]
    page_number = page["page_number"]

    # Detect street name
    street_match = re.search(
        r"STREET[:\s]+([A-Za-z0-9 \.\-']+)", text, re.IGNORECASE
    )
    if street_match:
        current_street = street_match.group(1).strip()

    for line in text.splitlines():
        if "|" not in line:
            continue

        cells = [c.strip() for c in line.split("|")]

        # Skip headers / separators
        if all(not c or re.match(r"^-+$", c) for c in cells):
            continue

        # ---- STREET NUMBER (sticky) ----
        if len(cells) > 1 and cells[1].isdigit():
            current_street_number = cells[1]

        # ---- TREE NUMBER ----
        if len(cells) <= 2 or not cells[2].isdigit():
            continue

        tree_no = int(cells[2])
        total_rows += 1

        # ---- SPECIES ----
        species_raw = cells[3] if len(cells) > 3 else None
        species = normalize_species(species_raw)

        if species and species.lower() in INVALID_SPECIES:
            species = None

        # ---- CLASSIFICATION ----
        if species:
            total_trees += 1
            species_counter[species] += 1
            street_counter[current_street] += 1
        else:
            species = "Blank"
            blank_spaces += 1

        # ---- RECORD ROW (ALWAYS) ----
        tree_rows.append({
            "street": current_street,
            "street_number": current_street_number,
            "tree_no": tree_no,
            "species": species,
            "page_number": page_number,
            "source_file": data["file_name"],
        })

# ---- WRITE CSV ----
csv_path = json_path.with_suffix(".csv")

with open(csv_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "street",
            "street_number",
            "tree_no",
            "species",
            "page_number",
            "source_file",
        ],
    )
    writer.writeheader()
    writer.writerows(tree_rows)

# ---- OUTPUT ----
print("\nTREE INVENTORY ANALYSIS")
print("----------------------------")
print(f"File: {data['file_name']}")
print(f"Pages processed: {data['page_count']}")
print(f"Total inventory positions: {total_rows}")
print(f"Planted trees: {total_trees}")
print(f"Blank (unplanted) spaces: {blank_spaces}")

print("\nTREES BY SPECIES (PLANTED ONLY)")
print("----------------------------")
for species, count in species_counter.most_common():
    print(f"{species:20} {count}")

print("\nTREES BY STREET (PLANTED ONLY)")
print("----------------------------")
for street, count in street_counter.items():
    print(f"{street:25} {count}")

print(f"\nCSV written to: {csv_path}")
