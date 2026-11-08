#!/usr/bin/env python3
"""PNG 파일명 매핑 / 알파 / 디자인허브 PNG 사전 검수 (v5)."""
from pathlib import Path
import argparse, csv, json, shutil
from PIL import Image
from miri_common import CSV_PATH, OUT, read_rows, norm, status_of, load_themes, make_element_name, make_keywords

IMAGE_DIR = OUT / "images"
REVIEW_DIR = OUT / "review"
READY_DIR = OUT / "upload_ready"
MAX_BYTES = 50 * 1024 * 1024
MIN_EDGE, MAX_EDGE = 700, 9800
MIN_DPI = 120
DPI_TOLERANCE = 0.5   # 120dpi로 저장해도 Pillow가 119.9896으로 읽는 반올림 오차 허용


def image_info(path):
    with Image.open(path) as im:
        im.load()
        w, h = im.size
        has_alpha = ("A" in im.getbands()) or ("transparency" in im.info)
        alpha_extrema = im.getchannel("A").getextrema() if "A" in im.getbands() else None
        if alpha_extrema:
            actual = alpha_extrema[0] < 255
        else:
            actual = "transparency" in im.info
        dpi = im.info.get("dpi", (None, None))
        dx = float(dpi[0]) if dpi and dpi[0] else None
        dy = float(dpi[1]) if dpi and len(dpi) > 1 and dpi[1] else dx
        return {"format": im.format or "", "width": w, "height": h, "alpha_channel": has_alpha,
                "actual_transparency": actual,
                "alpha_min": alpha_extrema[0] if alpha_extrema else "",
                "alpha_max": alpha_extrema[1] if alpha_extrema else "",
                "fully_transparent_pixel": bool(alpha_extrema and alpha_extrema[0] == 0),
                "dpi_x": round(dx, 2) if dx else "", "dpi_y": round(dy, 2) if dy else ""}


def set_dpi_120(path):
    """픽셀은 그대로 두고 DPI 메타데이터만 120으로 기록한다 (원본은 .orig로 보관하지 않으므로 사본에서 사용 권장)."""
    with Image.open(path) as im:
        im.load()
        fmt = im.format
        im2 = im.copy()
    if fmt != "PNG":
        return False
    im2.save(path, format="PNG", dpi=(MIN_DPI, MIN_DPI))
    return True


def main():
    ap = argparse.ArgumentParser(description="PNG 사전 검수 및 업로드 준비")
    ap.add_argument("--copy-ready", action="store_true", help="모든 기준 통과 PNG만 upload_ready 폴더에 복사")
    ap.add_argument("--fix-dpi", action="store_true", help="DPI 정보가 없거나 120 미만인 PNG에 120dpi 메타데이터를 기록")
    args = ap.parse_args()
    items, _ = read_rows()
    themes = load_themes()
    for d in (IMAGE_DIR, REVIEW_DIR, READY_DIR):
        d.mkdir(parents=True, exist_ok=True)
    if args.copy_ready:
        for old_ready in READY_DIR.glob('*.png'):
            old_ready.unlink()

    expected = {norm(i.get("filename")): i for i in items if norm(i.get("filename"))}
    actual = {norm(p.name): p for p in IMAGE_DIR.iterdir() if p.is_file() and p.suffix.lower() == ".png"}
    rows, ready_count, fixed = [], 0, 0

    for filename, item in expected.items():
        path = actual.get(filename)
        base = {"filename": filename, "subject": norm(item.get("subject")), "template_id": norm(item.get("template_id")),
                "file_found": bool(path), "format": "", "width": "", "height": "", "alpha_channel": False,
                "actual_transparency": False, "alpha_min": "", "alpha_max": "", "fully_transparent_pixel": "",
                "dpi_x": "", "dpi_y": "", "size_mb": "", "checks": "", "status": "MISSING"}
        if not path:
            base["checks"] = "PNG 파일 없음: CSV filename과 파일명을 확인"
            rows.append(base); continue
        try:
            info = image_info(path)
            if False and args.fix_dpi and info["format"] == "PNG" and (
                    not info["dpi_x"] or min(float(info["dpi_x"]), float(info["dpi_y"])) < MIN_DPI - DPI_TOLERANCE):
                if set_dpi_120(path):
                    fixed += 1
                    info = image_info(path)
            base.update(info)
            base["size_mb"] = round(path.stat().st_size / (1024 * 1024), 2)
            issues = []
            if info["format"] != "PNG": issues.append("PNG 형식 아님")
            if min(info["width"], info["height"]) < MIN_EDGE: issues.append(f"짧은 변 {MIN_EDGE}px 미만")
            if max(info["width"], info["height"]) > MAX_EDGE: issues.append(f"긴 변 {MAX_EDGE}px 초과")
            if not info["actual_transparency"]: issues.append("실제 투명 픽셀 없음(알파 채널/투명도 확인 필요)")
            elif not info["fully_transparent_pixel"]: issues.append("완전 투명 픽셀(alpha=0) 없음: 배경이 남아 있을 수 있음")
            if path.stat().st_size > MAX_BYTES: issues.append("50MB 초과")
            needs_dpi = not info["dpi_x"] or not info["dpi_y"] or min(float(info["dpi_x"]), float(info["dpi_y"])) < MIN_DPI - DPI_TOLERANCE
            if needs_dpi and not (args.fix_dpi and args.copy_ready):
                issues.append("DPI 메타데이터 120 미만 또는 없음 (--copy-ready --fix-dpi로 사본에 기록 가능)")
            base["checks"] = "; ".join(issues) if issues else "기본 파일 조건 통과"
            base["status"] = "READY" if not issues else "REVIEW"
            if not issues:
                ready_count += 1
                if args.copy_ready:
                    target = READY_DIR / path.name
                    shutil.copy2(path, target)
                    if needs_dpi and args.fix_dpi:
                        if set_dpi_120(target): fixed += 1
                        else: raise RuntimeError('DPI 사본 기록 실패')
        except Exception as e:
            base["status"] = "ERROR"
            base["checks"] = f"이미지 판독 실패: {type(e).__name__}: {e}"
        rows.append(base)

    for filename, path in actual.items():
        if filename not in expected:
            rows.append({"filename": filename, "file_found": True, "format": "PNG",
                         "size_mb": round(path.stat().st_size / (1024 * 1024), 2),
                         "checks": "CSV에 등록되지 않은 PNG 파일", "status": "UNMAPPED"})

    fields = ["filename", "subject", "template_id", "file_found", "format", "width", "height", "alpha_channel",
              "actual_transparency", "alpha_min", "alpha_max", "fully_transparent_pixel", "dpi_x", "dpi_y",
              "size_mb", "checks", "status"]
    report = REVIEW_DIR / "png_quality_report.csv"
    with report.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore"); w.writeheader(); w.writerows(rows)

    # 제출 준비표: 요소 이름·키워드는 CSV 값 우선, 없으면 자동 생성
    by_file = {norm(i.get("filename")): i for i in items}
    manifest = REVIEW_DIR / "upload_metadata_manifest.csv"
    with manifest.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["filename", "subject", "template_id", "ai_generated_checkbox", "content_type",
                                          "license_choice", "element_name_ko", "keywords_ko", "rights_review",
                                          "file_check", "tracking_status"])
        w.writeheader()
        for r in rows:
            if r["status"] == "UNMAPPED":
                continue
            it = by_file.get(r["filename"], {})
            tid = r["template_id"]
            name = norm(it.get("element_name")) or make_element_name(r["subject"], tid)
            kws = norm(it.get("keywords")) or ", ".join(make_keywords(r["subject"], tid, themes))
            w.writerow({"filename": r["filename"], "subject": r["subject"], "template_id": tid,
                        "ai_generated_checkbox": "필수 체크 (ChatGPT 이미지 생성)",
                        "content_type": "PNGelement", "license_choice": "Premium",
                        "element_name_ko": name, "keywords_ko": kws,
                        "rights_review": "제3자 저작권·상표·캐릭터 유사성 검토 필요",
                        "file_check": r["status"], "tracking_status": status_of(it)})

    counts = {}
    for r in rows: counts[r["status"]] = counts.get(r["status"], 0) + 1
    print("PNG 사전 검수 완료")
    print("상태:", json.dumps(counts, ensure_ascii=False))
    if args.fix_dpi: print(f"DPI 120 기록: {fixed}개")
    print("검수 보고서:", report)
    print("메타데이터 입력표:", manifest)
    if args.copy_ready:
        print(f"기본 조건 통과 파일 {ready_count}개를 업로드 준비 폴더에 복사했습니다: {READY_DIR}")
    else:
        print("업로드 폴더 복사는 실행하지 않았습니다. 결과 확인 후 --copy-ready 옵션을 사용하세요.")


if __name__ == "__main__":
    main()
