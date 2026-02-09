import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.ops import unary_union
from shapely.geometry import Point
import numpy as np

## -------------------------------------------------- IMPORT DATASETS --------------------------------------------------
#region

# Import datasets
df_u = pd.read_excel("Datasets/Uhrich Avenue - Usher Street.xlsx")
df_v = pd.read_excel("Datasets/Van Horne - Victory Crescent.xlsx")
df_y = pd.read_excel("Datasets/Yarnton-Young Crescent.xlsx")
df_z = pd.read_excel("Datasets/Zaran-Zech Place.xlsx")

#endregion

## -------------------------------------------- CLEAN AND CALCULATE COLUMNS --------------------------------------------
#region

# Dataset list
inventories = [df_u, df_v, df_y, df_z]

# Correct known errors between inventories and address point dataset
df_v.loc[df_v['Street'] == 'Victoria Avenue East', 'Street'] = 'Victoria Avenue'

# Forward fill Street, Block Start, Block End, Sector, Street Number
columns_to_fill = ['Street', 'Block Start', 'Block End', 'Sector', 'Street Number']

for inventory in inventories:
    # Forward fill columns
    for col in columns_to_fill:
        if col in inventory.columns:
            inventory[col] = inventory[col].ffill()

    # Assign Page Number based on changes in Block Start
    if 'Block Start' in inventory.columns:
        inventory['Page Number'] = inventory['Block Start'].ne(inventory['Block Start'].shift()).cumsum()

    # Clean Street Number: remove decimals and convert to string
    if 'Street Number' in inventory.columns:
        inventory['Street Number'] = pd.to_numeric(inventory['Street Number'], errors='coerce')
        inventory['Street Number'] = inventory['Street Number'].ffill().astype('Int64').astype(str)

    # Create Full Address
    if 'Street Number' in inventory.columns and 'Street' in inventory.columns:
        inventory['Full Address'] = (
            inventory['Street Number'].str.strip() + ' ' +
            inventory['Street'].astype(str).str.strip()
        )

# Assign Document column based on file name
df_u["Document"] = "Uhrich Avenue - Usher Street"
df_v["Document"] = "Van Horne - Victory Crescent"
df_y["Document"] = "Yarnton-Young Crescent"
df_z["Document"] = "Zaran-Zech Place"

#endregion

## -------------------------------------------------- MERGE DATASETS ---------------------------------------------------
#region

# Inventory names dictionary
inventories_dictionary = {
    "df_u": df_u,
    "df_v": df_v,
    "df_y": df_y,
    "df_z": df_z
}

# Check for missing columns
all_columns = set().union(*(df.columns for df in inventories_dictionary.values()))

print("Checking for missing columns in each dataframe:")

for name, df in inventories_dictionary.items():
    missing = all_columns - set(df.columns)
    if missing:
        print(f"{name} is missing: {missing}")
    else:
        print(f"{name} has all required columns.")

# Stack dataframes
for name, df in inventories_dictionary.items():
    missing = all_columns - set(df.columns)
    for col in missing:
        df[col] = pd.NA

# Concatenate dataframes
df = pd.concat(inventories_dictionary.values(), ignore_index=True)

# Print blank space
print("\n")

# Desired column order
desired_order = [
    'Street', 'Block Start', 'Block End', 'Sector', 'Street Number', 'Tree Number', 'Species', 'Year Planted',
    'Height - 1981', 'Height - 1985', 'Height - 1987', 'Height - 1988', 'Height - 1991',
    'Diameter - 1981', 'Diameter - 1985', 'Diameter - 1987', 'Diameter - 1988',
    'Comments', 'Document', 'Page Number', 'Full Address'
]

# Only keep columns that exist in the DataFrame (in case some are missing)
existing_columns = [col for col in desired_order if col in df.columns]
remaining_columns = [col for col in df.columns if col not in existing_columns]

# Reorder: desired columns first, others follow
df = df[existing_columns + remaining_columns]

#endregion

## ---------------------------------------------- SPECIES IDENTIFICATOIN -----------------------------------------------
#region

# Fill nan cells with Missing
df['Species'] = df['Species'].fillna("Blank")

# Species dictionary
species_dict = {
    "Amur cherry": "Prunus maackii",
    "Amur maple": "Acer tataricum subsp. ginnala",
    "Apple": "Malus spp.",
    "American basswood": "Tilia americana",
    "American elm": "Ulmus americana",
    "Barberry": "Berberis spp.",
    "Basswood": "Tilia americana",
    "Beaked willow": "Salix bebbiana",
    "Black poplar": "Populus nigra",
    "Bolleana poplar": "Populus alba 'Pyramidalis'",
    "Buffalo berry": "Shepherdia spp.",
    "Caragana": "Caragana arborescens",
    "Cedar": "Thuja occidentalis",
    "Cherry": "Prunus spp.",
    "Chokecherry": "Prunus virginiana var. virginiana",
    "Colorado spruce": "Picea pungens",
    "Cotoneaster": "Cotoneaster lucidus",
    "Cottonwood": "Populus deltoides ssp. monilifera",
    "Crabapple": "Malus spp.",
    "Cutleaf weeping birch": "Betula pendula 'Laciniata'",
    "Green ash": "Fraxinus pennsylvanica",
    "Juniper": "Juniperus scopulorum",
    "Lilac": "Syringa",
    "Littleleaf Linden": "Tilia cordata",
    "Manchurian elm": "Ulmus pumila",
    "Manitoba maple": "Acer negundo",
    "Mountain ash": "Sorbus americana",
    "Muckle plum": "Prunus x nigrella 'Muckle'",
    "Mugo pine": "Pinus mugo",
    "Paper birch": "Betula papyrifera",
    "Patmore ash": "Fraxinus pennsylvanica 'Patmore'",
    "Pine": "Pinus spp.",
    "Poplar": "Populus spp.",
    "Poplar - multistem": "Populus spp.",
    "Redosier Dogwood": "Cornus sericea",
    "Red osier dogwood": "Cornus sericea",
    "Rose bush": "Rosa spp.",
    "Russian almond": "Prunus tenella",
    "Russian olive": "Elaeagnus angustifolia",
    "Scotch pine": "Pinus sylvestris",
    "Shining willow": "Salix lucida",
    "Shubert chokecherry": "Prunus virginiana 'Schubert'",
    "Silver maple": "Acer saccharinum",
    "Trembling aspen": "Populus tremuloides",
    "Weeping birch": "Betula pendula",
    "White birch": "Betula papyrifera",
    "White spruce": "Picea glauca",
    "Willow": "Salix spp.",
    "Laurel willow": "Salix pentandra",
    "Pyramidal cedar": "Thuja occidentalis",
    "Fraxinus nigra": "Fraxinus nigra",
    "Pin cherry": "Prunus pensylvanica",
    "Honey suckle": "Lonicera spp.",
    "Aster": "Aster spp.",
    "Currant": "Ribes spp.",
    "Plum": "Prunus spp.",
    "Balsam poplar": "Populus balsamifera",
    "Largetooth aspen": "Populus grandidentata",
    "Royalty flowering crap": "Malus 'Royalty'",
    "European white birch": "Betula pendula",

    "Unclear": "Unclear",
    "Unknown": "Unclear",
    "Amier": "Unclear",

    "Blank": "No tree",
    "Vacant": "No tree",

    "Fence": "No space",
    "Fire hydrant": "No space",
    "Sign": "No space",
    "Water line": "No space",
    "Light": "No space",
    "Lamp post": "No space",
    "Telephone pole": "No space",
    "Sidewalk": "No space",
    "Parking": "No space",
    "Signpost": "No space",
    "Pole": "No space",
    "Street light": "No space",
    "Driveway": "No space",
    "No room": "No space"
}




# Create a botanical name column
df['Botanical Name'] = df['Species'].map(species_dict)

# Add a warning message if any species are missing from the dictionary
unmapped_species = df[df['Botanical Name'].isna()]['Species'].unique()
if len(unmapped_species) > 0:
    print("❌ The following species were not found in the species dictionary:")
    for species in unmapped_species:
        print(f" - {species}")
else:
    print("✅ All species were successfully mapped.")

print("\n")

#endregion

## ----------------------------------------------- TIE TO ADDRESS POINTS -----------------------------------------------
#region

# Import address points shapefile
address_points = gpd.read_file("Property Locations/address_points.shp") # columns STREET and FULLADDRSS

# Normalize street and address columns
df['Street'] = df['Street'].astype(str).str.strip().str.lower()
address_points['STREET'] = address_points['STREET'].astype(str).str.strip().str.lower()

df['Full Address'] = df['Full Address'].astype(str).str.strip().str.lower()
address_points['FULLADDRSS'] = address_points['FULLADDRSS'].astype(str).str.strip().str.lower()

# Unique values
unique_streets_df = set(df['Street'].dropna().unique())
streets_in_address_points = set(address_points['STREET'].dropna().unique())

unique_full_addresses = set(df['Full Address'].dropna().unique())
full_addresses_points = set(address_points['FULLADDRSS'].dropna().unique())

# Find unmatched
unmatched_streets = unique_streets_df - streets_in_address_points
unmatched_addresses = unique_full_addresses - full_addresses_points

# Print results for streets
if unmatched_streets:
    print("❌ Streets not found in address_points:")
    for street in sorted(unmatched_streets):
        print(f" - {street}")
else:
    print("✅ All streets found in address_points.")

# Print results for full addresses
if unmatched_addresses:
    print("\n❌ Full addresses not found in address_points:")
    for addr in sorted(unmatched_addresses):
        print(f" - {addr}")
else:
    print("\n✅ All full addresses found in address_points.")

#endregion

## -------------------------------------------------- PLOT LOCATIONS ---------------------------------------------------
#region

# Filter address_points to matched addresses
matched_address_gdf = address_points[address_points['FULLADDRSS'].isin(df['Full Address'])]

# Import road centerlines, current city boundary, and subdivision shapefiles
roads = gpd.read_file("Roads/road_centerline.shp")
boundary = gpd.read_file("City Limits/CityLimits.shp")
divisions = gpd.read_file("Subdivisions/YearofDevelopment.shp")

# Ensure CRS matches
target_crs = roads.crs
if boundary.crs != target_crs:
    boundary = boundary.to_crs(target_crs)
if divisions.crs != target_crs:
    divisions = divisions.to_crs(target_crs)

# Clip divisions to new city boundary
divisions_clipped = gpd.clip(divisions, boundary)

# Filter subdivisions where Year > 1990
recent_divisions = divisions_clipped[divisions_clipped['Year'] > 1985]
old_divisions = divisions_clipped[divisions_clipped['Year'] < 1985]

# Create a mask from year for divisions
merged_old = unary_union(old_divisions.geometry)
enclosed_old = merged_old.buffer(1).buffer(-1)  # adjust value based on units
old_divisions = gpd.GeoDataFrame(geometry=[enclosed_old], crs=old_divisions.crs)

# Clip city boundary by divisions
old_boundary = gpd.clip(boundary, old_divisions)

# Clip roads to city boundary
roads_clipped_new = gpd.clip(roads, recent_divisions)
roads_clipped_old = gpd.clip(roads, old_boundary)

# Plot
fig, ax = plt.subplots(figsize=(10, 10))

# Plot clipped roads
roads_clipped_old.plot(ax=ax, linewidth=0.5, edgecolor='gray')
roads_clipped_new.plot(ax=ax, linewidth=0.5, edgecolor='gray', alpha=0.6)

# Plot city boundary (transparent fill, black edge)
boundary.plot(ax=ax, linewidth=1, edgecolor='black', facecolor='none', alpha = 0.6)

# Plot old city boundary (transparent fill, black edge)
old_boundary.plot(ax=ax, linewidth=1.5, edgecolor='black', facecolor='none')

# Plot recent subdivisions
recent_divisions.plot(ax=ax, linewidth=1, facecolor='grey', alpha=0.075)

# Plot matched address points
matched_address_gdf.plot(ax=ax, markersize=3, color='green', alpha=0.7)

# Clean up plot
ax.set_axis_off()
plt.tight_layout()
plt.show()

#endregion

## ---------------------------------------- INTERPOLATE BETWEEN ADDRESS POINTS -----------------------------------------
#region

# Extract address number from full address
def extract_address_number(addr):
    try:
        return int(addr.split()[0])
    except:
        return np.nan


# Add numeric address number column
df['Address Number'] = df['Full Address'].apply(extract_address_number)
address_points['Address Number'] = address_points['FULLADDRSS'].apply(extract_address_number)

# Merge address_points with coordinates
address_points = address_points.dropna(subset=['Address Number', 'geometry'])

# Create a GeoDataFrame to hold interpolated results
interpolated_points = []

# Loop through unmatched addresses
for unmatched in unmatched_addresses:
    addr_num = extract_address_number(unmatched)
    if np.isnan(addr_num):
        continue  # skip if number is missing

    # Get street name
    street = unmatched.replace(str(addr_num), '').strip()

    # Get known points on the same street
    candidates = address_points[address_points['STREET'] == street]
    if len(candidates) < 2:
        continue  # not enough points to interpolate

    # Find lower and upper bounding addresses
    lower = candidates[candidates['Address Number'] < addr_num].sort_values('Address Number').tail(1)
    upper = candidates[candidates['Address Number'] > addr_num].sort_values('Address Number').head(1)

    if not lower.empty and not upper.empty:
        # Interpolate x and y
        lower_num = lower['Address Number'].values[0]
        upper_num = upper['Address Number'].values[0]
        lower_geom = lower.geometry.values[0]
        upper_geom = upper.geometry.values[0]

        ratio = (addr_num - lower_num) / (upper_num - lower_num)

        interpolated_x = lower_geom.x + (upper_geom.x - lower_geom.x) * ratio
        interpolated_y = lower_geom.y + (upper_geom.y - lower_geom.y) * ratio

        interpolated_points.append({
            'Full Address': unmatched,
            'Street': street,
            'Address Number': addr_num,
            'geometry': Point(interpolated_x, interpolated_y)
        })

# Create GeoDataFrame from interpolated points
interpolated_gdf = gpd.GeoDataFrame(interpolated_points, crs=address_points.crs)

print(f"\n✅ Interpolated {len(interpolated_gdf)} unmatched addresses.")

#endregion

## -------------------------------------------------- PLOT LOCATIONS WITH INTERPOLATED POINTS ---------------------------------------------------
#region

# Filter address_points to matched addresses
matched_address_gdf = address_points[address_points['FULLADDRSS'].isin(df['Full Address'])]

# Import road centerlines, current city boundary, and subdivision shapefiles
roads = gpd.read_file("Roads/road_centerline.shp")
boundary = gpd.read_file("City Limits/CityLimits.shp")
divisions = gpd.read_file("Subdivisions/YearofDevelopment.shp")

# Ensure CRS matches
target_crs = roads.crs
if boundary.crs != target_crs:
    boundary = boundary.to_crs(target_crs)
if divisions.crs != target_crs:
    divisions = divisions.to_crs(target_crs)

# Clip divisions to new city boundary
divisions_clipped = gpd.clip(divisions, boundary)

# Filter subdivisions where Year > 1990
recent_divisions = divisions_clipped[divisions_clipped['Year'] > 1985]
old_divisions = divisions_clipped[divisions_clipped['Year'] < 1985]

# Create a mask from year for divisions
merged_old = unary_union(old_divisions.geometry)
enclosed_old = merged_old.buffer(1).buffer(-1)  # adjust value based on units
old_divisions = gpd.GeoDataFrame(geometry=[enclosed_old], crs=old_divisions.crs)

# Clip city boundary by divisions
old_boundary = gpd.clip(boundary, old_divisions)

# Clip roads to city boundary
roads_clipped_new = gpd.clip(roads, recent_divisions)
roads_clipped_old = gpd.clip(roads, old_boundary)

# Plot
fig, ax = plt.subplots(figsize=(10, 10))

# Plot clipped roads
roads_clipped_old.plot(ax=ax, linewidth=0.5, edgecolor='gray')
roads_clipped_new.plot(ax=ax, linewidth=0.5, edgecolor='gray', alpha=0.6)

# Plot city boundary (transparent fill, black edge)
boundary.plot(ax=ax, linewidth=1, edgecolor='black', facecolor='none', alpha = 0.6)

# Plot old city boundary (transparent fill, black edge)
old_boundary.plot(ax=ax, linewidth=1.5, edgecolor='black', facecolor='none')

# Plot recent subdivisions
recent_divisions.plot(ax=ax, linewidth=1, facecolor='grey', alpha=0.075)

# Plot matched address points
matched_address_gdf.plot(ax=ax, markersize=3, color='green', alpha=0.7)

# Plot interpolated points
interpolated_gdf.plot(ax=ax, markersize=3, color='orange', alpha=0.7)

# Clean up plot
ax.set_axis_off()
plt.tight_layout()
plt.show()

#endregion
