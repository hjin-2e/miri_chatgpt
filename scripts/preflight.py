#!/usr/bin/env python3
"""Validate locally supplied PNGs; never generates or uploads images."""
import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image, UnidentifiedImageError

ROOT = Path(__file__).resolve().parents[1]
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--csv", type=Path, default=ROOT / "input/subjects.csv")
    p.add_argument("--images", type=Path, default=ROOT / "output/images")
    p.add_argument("--output", type=Path, default=ROOT / "data/status.json")
    p.add_argument("--min-size", type=int, default=512)
    args = p.parse_args()
    with args.csv.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    items = []
    for row in rows:
        name = Path(row.get("fileName", "").strip()).name
        if not name or name != row.get("fileName", "").strip() or not name.lower().endswith(".png"):
            print("SKIP unsafe or invalid fileName:", row.get("fileName", ""))
            continue
        item = {
            "elementName": row.get("elementName", "").strip(),
            "style": row.get("style", "").strip(),
            "fileName": name,
            "status": "planned",
            "updatedAt": datetime.now(timezone.utc).date().isoformat()
        }
        file = args.images / name
        if file.exists():
            try:
                with Image.open(file) as img:
                    rgba = img.convert("RGBA")
                    alpha = rgba.getchannel("A")
                    lo, hi = alpha.getextrema()
                    valid = (img.format == "PNG" and "A" in img.getbands()
                             and min(img.size) >= args.min_size and lo < 255)
                    item["status"] = "ready" if valid else "review"
                    item["check"] = {
                        "width": img.width, "height": img.height,
                        "hasTransparency": lo < 255,
                        "passed": valid
                    }
            except (UnidentifiedImageError, OSError, ValueError):
                item["status"] = "review"
        items.append(item)
    data = {"schemaVersion": 1, "updatedAt": datetime.now(timezone.utc).isoformat(), "items": items}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Checked {len(items)} records; ready={sum(x['status']=='ready' for x in items)}")
if __name__ == "__main__":
    main()
