"""재배 비용과 판매 수익 계산. 화면과 무관한 순수 계산이며, 단가는 모두 가정값이다."""

ELECTRICITY_PER_KWH = 80      # 원 (농사용 전력 요금 수준)
WATER_PER_L = 1.5             # 원
FERTILIZER_PER_G = 10         # 원

# 작물: (kg당 판매가, 파종 1회 종자·모종 비용) — 원
PRICES = {
    "상추":     (8000, 4000),
    "토마토":   (8000, 8000),
    "딸기":     (15000, 12000),
    "파프리카": (9000, 8000),
    "오이":     (5000, 5000),
    "시금치":   (7000, 3000),
}
DEFAULT_PRICE = (5000, 6000)


def grade_multiplier(quality):
    """품질(평균 건강도 %)에 따른 등급 단가 배수"""
    return 1.2 if quality >= 90 else 1.0 if quality >= 70 else 0.7


def cost_breakdown(species, kwh, water_l, fertilizer_g):
    """항목별 비용 [(이름, 원)]"""
    seed = PRICES.get(species, DEFAULT_PRICE)[1]
    return [("종자", seed), ("전기", kwh * ELECTRICITY_PER_KWH),
            ("물", water_l * WATER_PER_L), ("비료", fertilizer_g * FERTILIZER_PER_G)]


def revenue(species, kg, quality):
    return kg * PRICES.get(species, DEFAULT_PRICE)[0] * grade_multiplier(quality)


def cycle_result(c):
    """끝난 재배 기록 하나의 (비용, 수익, 순이익)"""
    cost = sum(v for _, v in cost_breakdown(c["species"], c["kwh"], c["water_l"], c["fertilizer_g"]))
    rev = revenue(c["species"], c["kg"], c["quality"]) if c["outcome"] == "수확" else 0
    return cost, rev, rev - cost


def totals(cycles):
    """여러 재배 기록의 (비용, 수익, 순이익) 합계"""
    rows = [cycle_result(c) for c in cycles]
    return tuple(sum(r[i] for r in rows) for i in range(3))


def won(v):
    return f"{v:,.0f}원"


def section_money(section):
    """진행 중인 재배의 현재 상태: 항목별 비용, 비용 합계, 예상 수익(작물이 없으면 None)"""
    p, ps = section.env_state.plant_profile, section.plant_state
    kwh, water, fert = section.cycle_usage()
    items = cost_breakdown(p.species, kwh, water, fert) if ps else [(n, 0) for n in ("종자", "전기", "물", "비료")]
    cost = sum(v for _, v in items)
    expected = None
    if ps and ps.alive:
        q = ps.avg_health
        expected = revenue(p.species, p.yield_kg * q / 100, q)
    return items, cost, expected
