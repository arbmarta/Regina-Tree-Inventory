import geopandas as gpd
import pandas as pd
import re

# ----------------------------
# Display settings
# ----------------------------
pd.set_option("display.max_columns", None)
pd.set_option("display.width", None)
pd.set_option("display.max_colwidth", None)

# ----------------------------
# Load data
# ----------------------------
address_points = gpd.read_file('../data/shapefiles/address_points.shp')
road_centerline = gpd.read_file('../data/shapefiles/road_centerline.shp')

# low_memory=False avoids dtype warnings; does NOT change data
trees = pd.read_csv('../data/tree_inventories_merged.csv', low_memory=False)

print("Loaded:")
print(f"  Address points: {len(address_points)}")
print(f"  Tree records: {len(trees)}")

# ----------------------------
# Inspection helpers
# ----------------------------
def inspect_gdf(name, gdf):
    print(f"\n{name} columns:")
    print(gdf.columns)
    print(f"\n{name} head (full):")
    print(gdf.head())

inspect_gdf("Address points", address_points)
inspect_gdf("Road centerline", road_centerline)

print("\nAddress points STREET column:")
print(address_points["STREET"].head())

print("\nTree inventory Street column:")
print(trees["Street"].head())

# ----------------------------
# Street normalization
# ----------------------------
RE_PUNCT = re.compile(r"[.,]")
RE_DASH_NOTE = re.compile(r"\s+-.*$")
RE_ORDINAL = re.compile(r"\b(\d+)\s+(st|nd|rd|th)\b")
RE_DIRECTION = re.compile(r"\b(north|south|east|west|n|s|e|w)\b$")

STREET_REPLACEMENTS = {
    r"\bst\b": "street",
    r"\brd\b": "road",
    r"\bdr\b": "drive",
    r"\bpl\b": "place",
    r"\bct\b": "court",
    r"\bcts\b": "courts",
    r"\bcres\b": "crescent",
    r"\bcrs\b": "crescent",
    r"\bave\b": "avenue",
}

def normalize_street(s):
    if pd.isna(s):
        return None

    s = str(s).lower().strip()
    if not s:
        return None

    # remove punctuation
    s = RE_PUNCT.sub("", s)

    # remove dash commentary (e.g. "- wascana centre side")
    s = RE_DASH_NOTE.sub("", s)

    # fix ordinal spacing: "21 st" → "21st"
    s = RE_ORDINAL.sub(r"\1\2", s)

    # normalize street types
    for pattern, repl in STREET_REPLACEMENTS.items():
        s = re.sub(pattern, repl, s)

    # remove trailing direction words
    s = RE_DIRECTION.sub("", s)

    # collapse whitespace
    s = re.sub(r"\s+", " ", s).strip()

    return s

# ----------------------------
# Normalize and compare
# ----------------------------
trees["_street_norm"] = trees["Street"].apply(normalize_street)
address_points["_street_norm"] = address_points["STREET"].apply(normalize_street)

tree_streets = set(trees["_street_norm"].dropna())
addr_streets = set(address_points["_street_norm"].dropna())

matched = tree_streets & addr_streets
unmatched = tree_streets - addr_streets

print(f"\nUnique tree streets: {len(tree_streets)}")
print(f"Unique address streets: {len(addr_streets)}")
print(f"\nMatched street names: {len(matched)}")
print(f"Unmatched tree streets: {len(unmatched)}")

print("\nSample unmatched tree street names:")
for s in sorted(unmatched)[:25]:
    print(f"  {s}")

print("\nSample matched street names:")
for s in sorted(matched)[:25]:
    print(f"  {s}")

# ----------------------------
# Address-level match check (UNIQUE addresses only)
# ----------------------------
print("\nChecking UNIQUE address-level matches using BUILDING + street name...")

# normalize BUILDING to string
address_points["_building_norm"] = (
    address_points["BUILDING"]
    .astype(str)
    .str.strip()
)

trees["_street_no_norm"] = (
    trees["Street Number"]
    .astype(str)
    .str.strip()
)

# build lookup from address points
addr_lookup = set(
    zip(
        address_points["_street_norm"],
        address_points["_building_norm"]
    )
)

# build UNIQUE addresses from tree inventory
tree_addresses = set(
    zip(
        trees["_street_norm"],
        trees["_street_no_norm"]
    )
)

# remove incomplete / invalid entries
tree_addresses = {
    (s, n)
    for s, n in tree_addresses
    if s and n and n != "nan"
}

matched_addresses = tree_addresses & addr_lookup
unmatched_addresses = tree_addresses - addr_lookup

print(f"\nUnique tree addresses: {len(tree_addresses)}")
print(f"Address-level matches found: {len(matched_addresses)}")
print(f"Address-level unmatched: {len(unmatched_addresses)}")

print("\nSample unmatched addresses:")
for street, number in sorted(unmatched_addresses, key=lambda x: (str(x[0]), str(x[1])))[:25]:
    print(f"  {number} {street}")

