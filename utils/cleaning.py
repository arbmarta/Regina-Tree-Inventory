import json
import csv
import re
from pathlib import Path
from collections import defaultdict

# PATHS
OCR_OUTPUT_DIR = Path("../data/ocr_output")
MERGED_JSON = Path("../data/tree_inventories_merged.json")
MERGED_CSV = Path("../data/tree_inventories_merged.csv")
SPECIES_MAP_PATH = Path("../data/species_map.json")

# Helpers
def clean(v):
    if v in (None, "", "nan"):
        return ""
    return str(v).strip()


def normalize_blank(v):
    if v in (None, "", "nan", "Blank"):
        return None
    return str(v).strip()


def load_species_map():
    if SPECIES_MAP_PATH.exists():
        return json.loads(SPECIES_MAP_PATH.read_text(encoding="utf-8"))
    return {}


def post_process_rows(rows, species_map):
    for r in rows:
        if r.get("Species"):
            s = r["Species"].lower().strip()

            # remove trailing punctuation
            s = re.sub(r"[.,;:]+$", "", s)
            r["Species"] = s

    for r in rows:
        species = r.get("Species")
        if species in species_map:
            r["Species"] = species_map[species]
        elif species:
            r["_unmapped"] = True

    prev_year = None
    for r in rows:
        yp = r.get("Year Planted")
        if yp and yp.strip() in ('"', "''", "\u201d", "\u201c", "\""):
            r["Year Planted"] = prev_year
        else:
            prev_year = yp

    for r in rows:
        yp = r.get("Year Planted") or ""
        if yp.upper() == "VACANT" and not r.get("Species"):
            r["Species"] = "vacant"
            r["Year Planted"] = None

    return rows


# Parser (structured extractor JSON)
def fields_by_name(field_list):
    return {f["name"]: f for f in field_list}


def row_by_name(row_list):
    return {f["name"]: f for f in row_list}


def parse_page_json(data, page_number=None):
    page = data["results"][0]
    raw_fields = page["extractions"][0]
    fields = fields_by_name(raw_fields)

    meta = {
        "street": clean(fields["street"]["value"]),
        "block": clean(fields["block"]["value"]),
        "sector": clean(fields["sector"]["value"]),
    }

    years = []
    for slot in range(1, 6):
        y = fields.get(f"year_{slot}", {}).get("value")
        if y and y != "nan":
            digits = re.sub(r"[^0-9]", "", y)
            if not digits:
                continue
            if digits != y.strip():
                print(f"  Warning [page {page_number}]: year_{slot} = '{y}' → {digits}")
            year = int(digits)
            if year < 100:
                year += 1900
            if year == 1880:
                year = 1990
            years.append(year)
    years = sorted(years)

    temp = defaultdict(dict)

    for slot, year in enumerate(years, start=1):
        for row_list in fields["table_row"]["value"]:
            row = row_by_name(row_list)

            key = (
                row["street_number"]["value"],
                row["tree_no"]["value"],
            )

            if key not in temp:
                temp[key] = {
                    "Street Number": row["street_number"]["value"],
                    "Tree No.": row["tree_no"]["value"],
                    "Species": normalize_blank(row["species"]["value"]),
                    "Year Planted": normalize_blank(row["year_planted"]["value"]),
                }

            h = row.get(f"height_{slot}", {}).get("value")
            d = row.get(f"diameter_{slot}", {}).get("value")

            temp[key][f"Height ({year})"] = normalize_blank(h)
            temp[key][f"Diameter ({year})"] = normalize_blank(d)

    rows = list(temp.values())

    for r in rows:
        r["Page"] = int(page_number)
        r["Street"] = meta["street"]
        r["Block"] = meta["block"]
        r["Sector"] = meta["sector"]

    return rows, years


# MAIN
def main():
    json_files = sorted(OCR_OUTPUT_DIR.glob("page_*.json"))
    print(f"Found {len(json_files)} JSON files")

    all_rows = []
    all_years = set()
    species_map = load_species_map()

    for jf in json_files:
        try:
            page_number = jf.stem.split("_")[1]
            data = json.loads(jf.read_text(encoding="utf-8"))
            rows, years = parse_page_json(data, page_number)
            rows = post_process_rows(rows, species_map)
            all_rows.extend(rows)
            all_years.update(years)
        except Exception as e:
            print(f"Error parsing {jf.name}: {e}")
            continue

    all_years = sorted(all_years)
    print(f"Parsed {len(all_rows)} tree records across {len(json_files)} pages")

    print(f"\nSurvey years found: {all_years}")

    mapped = sorted({r["Species"] for r in all_rows if r.get("Species") and not r.get("_unmapped")})
    unmapped = sorted({r["Species"] for r in all_rows if r.get("Species") and r.get("_unmapped")})

    print(f"\nMapped species ({len(mapped)}):")
    for s in mapped:
        print(f"  {s}")

    if unmapped:
        print(f"\nUnmapped species ({len(unmapped)}):")
        for s in unmapped:
            print(f"  {s}")

    # --- Save merged JSON ---
    MERGED_JSON.write_text(json.dumps(all_rows, indent=2), encoding="utf-8")

    # --- Save merged CSV ---
    base_cols = ["Page", "Street", "Block", "Sector", "Street Number", "Tree No.", "Species", "Year Planted"]
    height_cols = [f"Height ({y})" for y in all_years]
    diameter_cols = [f"Diameter ({y})" for y in all_years]

    year_cols = height_cols + diameter_cols

    fieldnames = base_cols + year_cols

    with open(MERGED_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in all_rows:
            writer.writerow({k: clean(row.get(k)) for k in fieldnames})

    print(f"\nSaved {MERGED_JSON}")
    print(f"Saved {MERGED_CSV}")


if __name__ == "__main__":
    main()