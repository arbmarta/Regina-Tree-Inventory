import json
import re
from collections import defaultdict

# =====================================================
# Helpers
# =====================================================

def clean(v):
    if v in (None, "", "nan"):
        return ""
    return str(v).strip()


def normalize_blank(v):
    if v in (None, "", "nan", "Blank"):
        return None
    return str(v).strip()


def print_table(meta, rows, years):
    print("\n" + "=" * 160)
    print(f"Street: {meta.get('street')}")
    print(f"Block : {meta.get('block')}")
    print(f"Sector: {meta.get('sector')}")
    print("-" * 160)

    base_headers = [
        "Street Number",
        "Tree No.",
        "Species",
        "Year Planted",
    ]

    # 🔑 Heights first, then diameters
    height_headers = [f"Height ({y})" for y in years]
    diameter_headers = [f"Diameter ({y})" for y in years]

    headers = base_headers + height_headers + diameter_headers

    widths = {h: len(h) for h in headers}
    for r in rows:
        for h in headers:
            widths[h] = max(widths[h], len(clean(r.get(h))))

    header_line = " | ".join(h.ljust(widths[h]) for h in headers)
    print(header_line)
    print("-" * len(header_line))

    for r in rows:
        print(
            " | ".join(clean(r.get(h)).ljust(widths[h]) for h in headers)
        )


def post_process_rows(rows):
    """Apply carry-down rules and normalization to parsed rows."""

    # 1) Lowercase species names
    for r in rows:
        if r.get("Species"):
            r["Species"] = r["Species"].lower()

    # 2) Where " is present in Year Planted, carry the value from the row above
    prev_year = None
    for r in rows:
        yp = r.get("Year Planted")
        if yp and yp.strip() in ('"', "''", "\u201d", "\u201c", "\""):
            r["Year Planted"] = prev_year
        else:
            prev_year = yp

    # 3) Where VACANT is in Year Planted but Species is blank, carry VACANT to Species
    for r in rows:
        yp = r.get("Year Planted") or ""
        if yp.upper() == "VACANT" and not r.get("Species"):
            r["Species"] = "vacant"
            r["Year Planted"] = None

    return rows


def collect_unique_species(rows):
    """Return sorted set of unique non-empty species values."""
    return sorted({r["Species"] for r in rows if r.get("Species")})


# =====================================================
# TRIAL 3 – Structured extractor
# =====================================================

def fields_by_name(field_list):
    return {f["name"]: f for f in field_list}


def row_by_name(row_list):
    return {f["name"]: f for f in row_list}


def parse_trial3_page(page):
    raw_fields = page["extractions"][0]
    fields = fields_by_name(raw_fields)

    meta = {
        "street": fields["street"]["value"],
        "block": fields["block"]["value"],
        "sector": fields["sector"]["value"],
    }

    years = []
    for slot in range(1, 6):
        y = fields.get(f"year_{slot}", {}).get("value")
        if y and y != "nan":
            years.append(int(y))
    years = sorted(years)

    temp = defaultdict(dict)

    for slot, year in enumerate(years, start=1):
        for row_list in fields["table_row"]["value"]:
            row = row_by_name(row_list)

            key = (
                row["street_number"]["value"],
                row["tree_no"]["value"]
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

            temp[key][f"Height ({year})"] = h
            temp[key][f"Diameter ({year})"] = d

    return meta, list(temp.values()), years


# =====================================================
# TRIAL 2 – Transcript, inline multi-year
# =====================================================

def extract_meta_from_transcript(text):
    meta = {}
    for key in ["STREET", "BLOCK", "SECTOR"]:
        m = re.search(rf"{key}[:\s]+(.+)", text, re.IGNORECASE)
        meta[key.lower()] = m.group(1).strip() if m else None
    return meta


def extract_years_from_transcript(text):
    m = re.search(r"\b(19\d{2})\s+(\d{2})\b", text)
    if not m:
        return []
    return [int(m.group(1)), 1900 + int(m.group(2))]


def parse_trial2_page(page):
    text = page["transcript"]
    meta = extract_meta_from_transcript(text)
    years = extract_years_from_transcript(text)

    temp = defaultdict(dict)
    current_street = None

    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue

        upper = line.upper()
        if (
            "STREET NUMBER" in upper
            or "HEIGHT FEET" in upper
            or "DIAMETER" in upper
            or set(line.replace("|", "").strip()) == {"-"}
        ):
            continue

        cells = [c.strip() or None for c in line.strip("|").split("|")]
        if len(cells) < 6:
            continue

        street_no, tree_no, species, year_planted, h_cell, d_cell = cells[:6]

        if street_no:
            current_street = street_no
        else:
            street_no = current_street

        if not tree_no:
            continue

        key = (street_no, tree_no)

        if key not in temp:
            temp[key] = {
                "Street Number": street_no,
                "Tree No.": tree_no,
                "Species": normalize_blank(species),
                "Year Planted": normalize_blank(year_planted),
            }

        heights = [] if not h_cell else h_cell.replace("--", "").split()
        diams   = [] if not d_cell else d_cell.replace("--", "").split()

        for i, year in enumerate(years):
            h = heights[i] if i < len(heights) else None
            d = diams[i] if i < len(diams) else None

            temp[key][f"Height ({year})"] = h
            temp[key][f"Diameter ({year})"] = d

    return meta, list(temp.values()), years


# =====================================================
# MAIN
# =====================================================

with open("trial2.json", "r", encoding="utf-8") as f:
    data = json.load(f)

doc = data[0]

all_species = set()

for page in doc["results"]:
    if "extractions" in page:
        meta, rows, years = parse_trial3_page(page)
    else:
        meta, rows, years = parse_trial2_page(page)

    rows = post_process_rows(rows)
    all_species.update(collect_unique_species(rows))

    print_table(meta, rows, years)

# Print all unique species
print("\n" + "=" * 60)
print("UNIQUE SPECIES")
print("=" * 60)
for s in sorted(all_species):
    print(f"  {s}")
print(f"\nTotal unique species: {len(all_species)}")