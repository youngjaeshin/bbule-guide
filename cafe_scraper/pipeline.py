#!/usr/bin/env python3
"""
네이버 카페 클리커 정산 스크래퍼 파이프라인

게임 "대용병시대 뿔레전쟁" 네이버 카페의 클리커 정산 게시판에서
글 메타데이터 + 스크린샷 이미지를 수집하고, DPS 값을 추출하여 랭킹표를 만든다.

사용법:
    # Step 1: 글 메타데이터 + 이미지 수집
    python pipeline.py fetch

    # Step 2: 이미지 상단 DPS 영역 크롭/확대
    python pipeline.py crop

    # Step 3: DPS 값을 수동 입력 또는 비전 에이전트 결과 입력
    python pipeline.py parse_dps --input dps_readings.json

    # Step 4: 최종 랭킹 생성
    python pipeline.py rank

비전 에이전트 위임 방법은 AGENT_INSTRUCTIONS.md 참고.
"""

import json
import os
import re
import sys
import urllib.request
from pathlib import Path

# ── 설정 ──────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
CONFIG = json.loads((BASE_DIR / "config.json").read_text())

CAFE_ID = CONFIG["cafe_id"]
MENU_ID = CONFIG["menu_id"]
API_BASE = CONFIG["api_base"]
IMG_SUFFIX = CONFIG["image_suffix"]

DATA_DIR = BASE_DIR / "data"
IMG_DIR = BASE_DIR / "images" / "raw"
CROP_DIR = BASE_DIR / "images" / "dps_crops"

HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://cafe.naver.com/"}


# ── Step 1: Fetch ─────────────────────────────────────────────────
def fetch_articles():
    """게시판의 모든 글 메타데이터 + 이미지 URL 수집"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    id_start, id_end = CONFIG["article_id_range"]
    articles = []

    print(f"Scanning articles {id_start} ~ {id_end}...")
    for aid in range(id_start, id_end + 1):
        url = API_BASE.format(cafe_id=CAFE_ID, article_id=aid)
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            data = json.loads(urllib.request.urlopen(req, timeout=10).read())
            article = data["result"]["article"]

            if article.get("menu", {}).get("id") != MENU_ID:
                continue

            content = article.get("contentHtml", "")
            img_urls = re.findall(r'src="(https://cafeptthumb[^"]+)"', content)
            nick = data["result"].get("writer", {}).get("nick", "?")

            meta = {
                "article_id": aid,
                "title": article["subject"],
                "nick": nick,
                "image_count": len(img_urls),
                "images": img_urls[:4],
            }
            meta.update(parse_title(article["subject"], nick))
            articles.append(meta)
            print(f"  OK {aid}: {article['subject']} ({len(img_urls)} imgs)")

        except Exception:
            pass  # 삭제/비공개 글 무시

    out = DATA_DIR / "articles_all.json"
    out.write_text(json.dumps(articles, ensure_ascii=False, indent=2))
    print(f"\n=> {len(articles)}건 저장: {out}")
    return articles


def parse_title(title, fallback_nick="?"):
    """제목에서 메타데이터 파싱

    형식: 2월/닉네임/덱타입/색단/각성수(메인+서브1+서브2)/비고
    형식이 다를 수 있으므로 유연하게 처리
    """
    parts = [p.strip() for p in title.split("/")]
    result = {
        "month": parts[0] if len(parts) > 0 else "",
        "nick_from_title": parts[1] if len(parts) > 1 else fallback_nick,
        "deck": "",
        "color": "",
        "awakening_total": 0,
        "awakening_detail": "",
        "extra": "",
    }

    # parts[2:] 에서 각성수 패턴을 먼저 찾기
    awakening_idx = -1
    for i in range(2, len(parts)):
        p = parts[i].strip()
        # 각성수 패턴: 숫자(...) 또는 접두어+숫자(...)
        m = re.search(r"(\d+)\((\d+)\+(\d+)\+(\d+)\)", p)
        if m:
            result["awakening_total"] = int(m.group(1))
            result["awakening_detail"] = f"{m.group(2)}+{m.group(3)}+{m.group(4)}"
            awakening_idx = i
            break
        # 단순 숫자 (소수의 경우)
        m2 = re.match(r"^(\d+)(?:\+(\d+))?$", p)
        if m2 and int(m2.group(1)) > 5:  # 5 이하는 각성수가 아닐 가능성
            result["awakening_total"] = int(m2.group(1)) + (
                int(m2.group(2)) if m2.group(2) else 0
            )
            awakening_idx = i
            break

    # 각성수 앞의 필드들을 덱/색단으로 배정
    pre_fields = parts[2:awakening_idx] if awakening_idx > 2 else parts[2:4]
    if len(pre_fields) >= 2:
        result["deck"] = pre_fields[0]
        result["color"] = pre_fields[1]
    elif len(pre_fields) == 1:
        result["deck"] = pre_fields[0]

    # 각성수 뒤의 필드들은 비고
    if awakening_idx > 0 and awakening_idx + 1 < len(parts):
        result["extra"] = "/".join(parts[awakening_idx + 1 :])
    elif awakening_idx == -1 and len(parts) > 4:
        result["extra"] = "/".join(parts[4:])

    return result


# ── Step 2: Download + Crop ───────────────────────────────────────
def download_and_crop():
    """모든 이미지 다운로드 + 상단 DPS 영역 크롭/확대"""
    from PIL import Image

    IMG_DIR.mkdir(parents=True, exist_ok=True)
    CROP_DIR.mkdir(parents=True, exist_ok=True)

    articles = json.loads((DATA_DIR / "articles_all.json").read_text())
    crop_cfg = CONFIG["image_crop"]

    for a in articles:
        aid = a["article_id"]
        for i, url in enumerate(a["images"][:3]):
            raw_path = IMG_DIR / f"{aid}_img{i+1}.png"
            crop_path = CROP_DIR / f"{aid}_img{i+1}_dps.png"

            # Download
            if not (raw_path.exists() and raw_path.stat().st_size > 1000):
                try:
                    dl_url = url + IMG_SUFFIX if "?" not in url else url
                    req = urllib.request.Request(dl_url, headers=HEADERS)
                    data = urllib.request.urlopen(req, timeout=15).read()
                    raw_path.write_bytes(data)
                except Exception as e:
                    print(f"  FAIL download {aid}_img{i+1}: {e}")
                    continue

            # Crop top DPS area + enlarge
            if not crop_path.exists():
                try:
                    img = Image.open(raw_path)
                    w, h = img.size
                    crop = img.crop(
                        (0, 0, int(w * crop_cfg["left_ratio"]), int(h * crop_cfg["top_ratio"]))
                    )
                    scale = crop_cfg["enlarge"]
                    crop = crop.resize(
                        (crop.width * scale, crop.height * scale), Image.LANCZOS
                    )
                    crop.save(crop_path)
                except Exception as e:
                    print(f"  FAIL crop {aid}_img{i+1}: {e}")
                    continue

        print(f"OK {aid}: {a['nick']}")

    print(f"\n=> 크롭 완료: {CROP_DIR}")


# ── Step 3: DPS 파싱 ─────────────────────────────────────────────
def parse_korean_number(s):
    """한국어 숫자 파싱: '4경 4999조' → int"""
    s = s.replace(",", "").strip()
    total = 0
    units = {"경": 10**16, "조": 10**12, "억": 10**8, "만": 10**4}
    remaining = s
    for unit, mult in units.items():
        if unit in remaining:
            left, remaining = remaining.split(unit, 1)
            num_str = left.strip()
            if num_str:
                try:
                    total += int(num_str) * mult
                except ValueError:
                    pass
            remaining = remaining.strip()
    if remaining:
        try:
            total += int(remaining)
        except ValueError:
            pass
    return total


def format_korean(n):
    """숫자를 한국어 단위로 포맷"""
    if n >= 10**16:
        return f"{n // 10**16}경 {(n % 10**16) // 10**12}조"
    elif n >= 10**12:
        return f"{n // 10**12}조 {(n % 10**12) // 10**8}억"
    elif n >= 10**8:
        return f"{n // 10**8}억 {(n % 10**8) // 10**4}만"
    elif n >= 10**4:
        return f"{n // 10**4}만 {n % 10**4}"
    else:
        return f"{n:,}"


def load_dps_readings(path):
    """비전 에이전트가 생성한 DPS 읽기 결과 로드

    형식: [{"article_id": 140198, "dps_items": {"물리 DPS": "163,474", ...}}, ...]
    """
    data = json.loads(Path(path).read_text())
    result = {}
    for entry in data:
        aid = entry["article_id"]
        total = 0
        for label, val in entry.get("dps_items", {}).items():
            total += parse_korean_number(str(val))
        result[aid] = {
            "total_dps": total,
            "total_dps_formatted": format_korean(total),
            "dps_items": entry.get("dps_items", {}),
        }
    return result


# ── Step 4: 랭킹 생성 ────────────────────────────────────────────
def generate_ranking(dps_path):
    """메타데이터 + DPS를 결합하여 랭킹표 생성"""
    articles = json.loads((DATA_DIR / "articles_all.json").read_text())
    dps_data = load_dps_readings(dps_path)

    # Merge
    for a in articles:
        aid = a["article_id"]
        if aid in dps_data:
            a.update(dps_data[aid])
        else:
            a["total_dps"] = 0
            a["total_dps_formatted"] = "미측정"
            a["dps_items"] = {}

    # Sort by DPS descending
    articles.sort(key=lambda x: x.get("total_dps", 0), reverse=True)

    # Save ranking
    out = DATA_DIR / "ranking.json"
    out.write_text(json.dumps(articles, ensure_ascii=False, indent=2))

    # Print table
    print(f"\n{'순위':>4} {'닉네임':<12} {'덱':>8} {'색단':>6} {'각성수':>8} {'합산 DPS':>16} {'비고'}")
    print("-" * 80)
    for i, a in enumerate(articles, 1):
        print(
            f"{i:>4} {a.get('nick','?'):<12} {a.get('deck','?'):>8} "
            f"{a.get('color','?'):>6} {a.get('awakening_total',0):>8,} "
            f"{a.get('total_dps_formatted','?'):>16} {a.get('extra','')}"
        )

    print(f"\n=> 랭킹 저장: {out}")
    return articles


# ── CLI ───────────────────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]

    if cmd == "fetch":
        fetch_articles()
    elif cmd == "crop":
        download_and_crop()
    elif cmd == "parse_dps":
        if len(sys.argv) < 4 or sys.argv[2] != "--input":
            print("Usage: pipeline.py parse_dps --input dps_readings.json")
            return
        result = load_dps_readings(sys.argv[3])
        out = DATA_DIR / "dps_parsed.json"
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2))
        print(f"=> {len(result)}건 파싱 완료: {out}")
    elif cmd == "rank":
        if len(sys.argv) >= 4 and sys.argv[2] == "--input":
            generate_ranking(sys.argv[3])
        else:
            generate_ranking(DATA_DIR / "dps_readings.json")
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
