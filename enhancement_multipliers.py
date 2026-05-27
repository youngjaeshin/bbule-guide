# Equipment 20강 enhancement multipliers
# Default: x6.0 for almost all items
# Exception 1: mainType=0 (데미지) items -> x4.0
# Exception 2: 2 specific 클릭 데미지 items -> x4.0
# Exception 3: 15 individual item overrides below

# Items with x4.0 multiplier (mainType=0 데미지 + 2 클릭 데미지)
ENHANCEMENT_X4_ITEMS = {
    "강철 검",
    "강철 망치 [마운틴]",
    "객갱박사의 발명품 [HGP-7]",
    "검투사 노예의 너클",
    "검투사의 구리검",
    "괴수의 갈비뼈",
    "낡은 단창",
    "닌자 단검",
    "단검 [꼬인 위치]",
    "데메테르의 팔찌",
    "돌도끼",
    "드로우 엘프 숏 소드",
    "딕 소드",
    "레이븐의 발톱",
    "롱 소드",
    "룬 배틀 엑스",
    "명검 [하트시커]",
    "명견 또치의 목걸이",
    "볼트 오브 객갱",
    "부러진 검",
    "붉은 검 [드레이크 팽]",
    "블랙 스틸 모닝 스타",
    "뿔레의 검",
    "산성 혈액 결정",
    "쇠 망치",
    "숏 소드",
    "숙련된 병사의 투구",
    "아낙수나문의 새끼거미",
    "악마의 손톱",
    "우프레틴의 전투 도끼",
    "이그레의 마도서 [리브로]",
    "자이다의 헬버드",
    "장검 [베놈 디펜더]",
    "전설의 뿅망치",
    "전투 도끼 [본 커터]",
    "정규군의 단검",
    "제이나의 하사품 [그레이스 포일]",
    "철칠여골타",
    "칼라무쉬 치즈",
    "콰소스 더스트",
    "크사르팍스의 위대함",
    "토르의 망치",
    "흔한 권총",
}

# Individual item overrides (not x4 or x6)
ENHANCEMENT_OVERRIDES = {
    "곤충 날개": 4.5,  # x4.5000
    "럭키 스톤": 5.142857,  # x5.1429
    "베멜루스의 검": 5.208333,  # x5.2083
    "다크 란도셀": 5.25,  # x5.2500
    "마법의 조랑말": 5.538462,  # x5.5385
    "영혼의 등불": 6.642857,  # x6.6429
    "브랜누스의 면갑": 6.75,  # x6.7500
    "젤다의 혼돈의 두건": 6.75,  # x6.7500
    "플랫 어스 스톤": 6.75,  # x6.7500
    "희생의 방패": 7.0,  # x7.0000
    "카우걸 밀크": 7.5,  # x7.5000
    "하늘 나무의 뿌리": 7.5,  # x7.5000
    "타이탄의 피 결정": 7.5,  # x7.5000
    "미래의 깃털": 7.5,  # x7.5000
    "궁창의 구슬": 7.5,  # x7.5000
}

def get_enhancement_multiplier(item_name, main_type=None):
    """Return 20강/0강 multiplier for an equipment item."""
    if item_name in ENHANCEMENT_OVERRIDES:
        return ENHANCEMENT_OVERRIDES[item_name]
    if item_name in ENHANCEMENT_X4_ITEMS or main_type == 0:
        return 4.0
    return 6.0
