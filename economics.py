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


def base_price(species):
    return PRICES.get(species, DEFAULT_PRICE)[0]


def revenue(species, kg, quality, price=None):
    """price: 그때의 kg당 시세. 없으면 기준가"""
    return kg * (price if price is not None else base_price(species)) * grade_multiplier(quality)


def cycle_result(c):
    """끝난 재배 기록 하나의 (비용, 수익, 순이익)"""
    cost = sum(v for _, v in cost_breakdown(c["species"], c["kwh"], c["water_l"], c["fertilizer_g"]))
    rev = revenue(c["species"], c["kg"], c["quality"], c.get("price")) if c["outcome"] == "수확" else 0
    return cost, rev, rev - cost


def totals(cycles):
    """여러 재배 기록의 (비용, 수익, 순이익) 합계"""
    rows = [cycle_result(c) for c in cycles]
    return tuple(sum(r[i] for r in rows) for i in range(3))


def won(v):
    return f"{v:,.0f}원"


def section_money(section, price=None):
    """진행 중인 재배의 현재 상태: 항목별 비용, 비용 합계, 예상 수익(작물이 없으면 None)"""
    p, ps = section.env_state.plant_profile, section.plant_state
    kwh, water, fert = section.cycle_usage()
    items = cost_breakdown(p.species, kwh, water, fert) if ps else [(n, 0) for n in ("종자", "전기", "물", "비료")]
    cost = sum(v for _, v in items)
    expected = None
    if ps and ps.alive:
        q = ps.avg_health
        expected = revenue(p.species, p.yield_kg * q / 100, q, price)
    return items, cost, expected


# 시세 이외에 재배 1일당 드는 전기·물·비료 비용 (처음 몇 번은 기록이 없어서 쓰는 어림값)
RESOURCE_COST_PER_DAY = {"상추": 1500, "토마토": 3100, "딸기": 2600, "파프리카": 4200, "오이": 3300, "시금치": 1800}
DEFAULT_RESOURCE_COST_PER_DAY = 3000


def daily_profit(species, yield_kg, grow_days, price, cycles):
    """지금 시세로 심었을 때 예상되는 하루당 순이익. 이미 키워 본 작물은 실제 사용 비용을 쓴다."""
    seed = PRICES.get(species, DEFAULT_PRICE)[1]
    past = [c for c in cycles if c["species"] == species and c["days"] > 0]
    if past:
        daily_cost = sum(c["kwh"] * ELECTRICITY_PER_KWH + c["water_l"] * WATER_PER_L
                         + c["fertilizer_g"] * FERTILIZER_PER_G for c in past) / sum(c["days"] for c in past)
    else:
        daily_cost = RESOURCE_COST_PER_DAY.get(species, DEFAULT_RESOURCE_COST_PER_DAY)
    income = yield_kg * price * grade_multiplier(95)
    return (income - seed - daily_cost * grow_days) / grow_days


def best_crop(profiles, prices, cycles):
    """profiles: {작물: PlantProfile}, prices: {작물: 현재 시세}. 하루당 예상 순이익이 가장 큰 작물 이름"""
    return max(profiles, key=lambda n: daily_profit(n, profiles[n].yield_kg, profiles[n].grow_days, prices[n], cycles))
