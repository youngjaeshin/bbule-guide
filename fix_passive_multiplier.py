#!/usr/bin/env python3
"""
fix_passive_multiplier.py
패시브 값 보정 (원본 엑셀값 기준):
- A등급: ÷1.1
- 기타 등급: ÷1.3
- 나눈 결과가 깔끔하지 않으면 원본 유지 (해당 값은 곱해진 게 아님)
주의: build_mercenary_passive.py 실행 직후 (원본 엑셀값 상태)에서 실행할 것.
"""

import json
import re

MERC_JSON = 'web/data_mercenaries.json'
INDEX_HTML = 'web/index.html'


def is_clean(val):
    """나눈 결과가 '깔끔한' 숫자인지 판별."""
    if val == 0:
        return False
    # 매우 작은 값 (0.005 미만)은 깔끔하지 않음
    if abs(val) < 0.005:
        return False
    # 정수에 가까움 (0.5 이상일 때만)
    if val >= 0.5 and abs(val - round(val)) < 0.01:
        return True
    # 소수 1자리에 가까움
    if abs(val - round(val, 1)) < 0.003:
        return True
    # 소수 2자리에 가까움
    if abs(val - round(val, 2)) < 0.001:
        return True
    return False


def fmt_number(val):
    """숫자를 깔끔하게 포맷."""
    if val >= 0.5 and abs(val - round(val)) < 0.01:
        return str(int(round(val)))
    r1 = round(val, 1)
    if abs(val - r1) < 0.003:
        return f"{r1:g}"
    r2 = round(val, 2)
    return f"{r2:g}"


def fmt_original(val):
    """원본 값 포맷 (그대로 유지하되 깔끔하게)."""
    if abs(val - round(val)) < 0.001:
        return str(int(round(val)))
    # 기존 소수점 자릿수 유지
    r3 = round(val, 3)
    return f"{r3:g}"


def fix_passive_text(text, divisor):
    """패시브 텍스트 내 숫자를 divisor로 나눔.
    현재값 = 원본 엑셀값 (빌드 직후 상태)."""

    def replace_num(match):
        original_str = match.group(0)
        original_val = float(original_str)
        if original_val == 0:
            return original_str

        corrected = original_val / divisor

        if is_clean(corrected):
            return fmt_number(corrected)
        else:
            # 깔끔하지 않으면 원본 유지
            return original_str

    return re.sub(r'\d+\.?\d*', replace_num, text)


def main():
    with open(MERC_JSON, 'r', encoding='utf-8') as f:
        mercs = json.load(f)

    print("=== 패시브 보정 (원본→나누기, 안떨어지면 원본유지) ===\n")

    changed = 0
    reverted = 0

    for m in mercs:
        if not m.get('passive'):
            continue

        grade = m['grade']
        divisor = 1.1 if grade == 'A' else 1.3

        old = m['passive']
        new = fix_passive_text(old, divisor)

        if old != new:
            changed += 1
            if changed <= 30:
                print(f"[{grade}] {m['name']}")
                print(f"  원본: {old}")
                print(f"  보정: {new}\n")

        m['passive'] = new

    print(f"총 {changed}건 변경됨\n")

    # 최종 확인: 소수점 있는 값 출력
    print("=== 최종 패시브 전체 ===\n")
    for m in mercs:
        p = m.get('passive')
        if p:
            print(f"[{m['grade']}] {m['name']}: {p}")

    # JSON 저장
    with open(MERC_JSON, 'w', encoding='utf-8') as f:
        json.dump(mercs, f, ensure_ascii=False, indent=1)
    print(f"\n{MERC_JSON} 저장 완료")

    # inline MERC_DATA 업데이트
    with open(INDEX_HTML, 'r', encoding='utf-8') as f:
        html = f.read()

    lines = html.split('\n')
    for i, line in enumerate(lines):
        if line.startswith('const MERC_DATA='):
            minified = json.dumps(mercs, ensure_ascii=False, separators=(',', ':'))
            lines[i] = f'const MERC_DATA={minified};'
            break

    with open(INDEX_HTML, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f"{INDEX_HTML} MERC_DATA 업데이트 완료")


if __name__ == '__main__':
    main()
