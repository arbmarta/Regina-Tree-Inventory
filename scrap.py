import json, csv

with open('data/species_map.json') as f:
    data = json.load(f)

with open('data/species_map.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['key', 'value'])
    for k, v in data.items():
        writer.writerow([k, v])