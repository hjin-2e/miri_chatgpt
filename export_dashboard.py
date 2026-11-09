#!/usr/bin/env python3
"""Export public-only status JSON for the portfolio /miri dashboard.

Reads existing input/subjects.csv without modifying it. No email or credentials
are exported. Missing PNGs are reported as planned (not upload-ready).
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from miri_common import read_rows, norm, status_of

ROOT = Path(__file__).resolve().parent
STYLE_LABELS = {
    "cute_3d_icon": "Cute 3D Icon",
    "clear_bubble": "Clear Bubble",
    "wax_crayon": "Wax Crayon",
    "soft_oil_pastel": "Soft Oil Pastel",
    "naive_doodle": "Naive Doodle",
    "soft_watercolor": "Soft Watercolor",
}
STATUS_LABELS = {
    "pending": "planned",
    "generated": "review",
    "submitted": "review",
    "approved": "approved",
    "rejected": "rejected",
}
def export(destination: Path):
    rows, _ = read_rows()
    items = []
    for row in rows:
        filename = norm(row.get("filename"))
        if not filename or Path(filename).name != filename or not filename.lower().endswith(".png"):
            continue
        status = status_of(row)
        image_exists = (ROOT / "output" / "images" / filename).is_file()
        # "ready" requires explicit local PNG preflight confirmation; never
        # infer ready merely from a generated/submitted status.
        display_status = STATUS_LABELS.get(status, "review")
        if status == "pending" and image_exists:
            display_status = "review"
        updated = norm(row.get("reviewed_at")) or norm(row.get("submitted_at"))
        items.append({
            "elementName": norm(row.get("element_name")) or norm(row.get("subject")),
            "style": STYLE_LABELS.get(norm(row.get("template_id")), norm(row.get("template_id"))),
            "fileName": filename,
            "status": display_status,
            "updatedAt": updated[:10] if updated else None,
        })
    data = {
        "schemaVersion": 1,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "items": items,
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"대시보드 상태 JSON 생성: {destination} ({len(items)}개)")
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, default=ROOT / "output" / "dashboard_status.json")
    args = p.parse_args()
    export(args.output)
if __name__ == "__main__":
    main()
