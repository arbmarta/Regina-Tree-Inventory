import json
from pathlib import Path

log = json.loads(Path("data/processing_log.json").read_text())
submitted = sorted([int(k) for k, v in log.items() if v["status"] == "submitted"])
print(f"Submitted: {submitted[0]} → {submitted[-1]}, count: {len(submitted)}")