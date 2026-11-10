"""여러 창이 함께 쓰는 상수, 작물 목록, 농장 만들기"""
from main import PlantProfile, EnvState, PlantState, FarmSection, Farm, LEAFY_STAGES, FRUIT_STAGES

DT = 1 / 6              # 한 단계 = 10분
HISTORY = 6 * 24        # 그래프에 남길 단계 수 (24시간)
FONT = "Malgun Gothic"

COLOR = {
    "bg": "#f3f5f1", "card": "#ffffff", "line": "#c9d3cb", "ink": "#1d2620", "muted": "#6b7a70",
    "healthy": "#2f7d4a", "closed": "#c0582a", "dead": "#7a7a7a", "band": "#e1eee4",
    "night": "#e6e9ef", "plot": "#1f6fb2", "on": "#2f7d4a", "off": "#d9dfda",
    "ready": "#b8860b", "empty": "#f7f8f6",
}

# 작물, 적정 온도, 최소 조도, 적정 토양 습도, 적정 습도, 적정 EC, 재배 일수, 수확량(kg), 생육 단계
PROFILES = [
    ("상추",     (15, 22), 15000, (55, 75), (60, 80), (1.0, 1.6), 6,  120.0,  LEAFY_STAGES),
    ("토마토",   (18, 27), 30000, (60, 80), (60, 80), (2.0, 3.5), 12, 360.0, FRUIT_STAGES),
    ("딸기",     (17, 25), 25000, (55, 75), (60, 75), (0.8, 1.4), 10, 150.0, FRUIT_STAGES),
    ("파프리카", (20, 27), 30000, (60, 80), (60, 80), (2.0, 3.0), 12, 300.0, FRUIT_STAGES),
    ("오이",     (20, 28), 25000, (65, 85), (70, 90), (1.8, 2.5), 8,  450.0, FRUIT_STAGES),
    ("시금치",   (15, 20), 15000, (55, 75), (60, 80), (1.5, 2.0), 6,  90.0,  LEAFY_STAGES),
]


def make_profile(name):
    _, temp, lux, soil, hum, ec, days, kg, stages = next(p for p in PROFILES if p[0] == name)
    return PlantProfile(name, temp, lux, soil, humidity_range=hum, nutrient_range=ec,
                        grow_days=days, yield_kg=kg, stages=stages)

# 그래프: (제목, 값 꺼내는 함수, y축 범위, 적정 범위 함수, 단위)
CHARTS = [
    ("온도",      lambda s: s.env_state.temperature,   (0, 40),     lambda p: p.temperature_range, "°C"),
    ("습도",      lambda s: s.env_state.humidity,      (20, 100),   lambda p: p.humidity_range, "%"),
    ("토양 습도", lambda s: s.env_state.soil_humidity, (0, 100),    lambda p: p.soil_humidity_range, "%"),
    ("양액 EC",   lambda s: s.env_state.nutrient,      (0, 4),      lambda p: p.nutrient_range, "mS/cm"),
    ("조도",      lambda s: s.env_state.luminosity,    (0, 70000),  lambda p: (p.min_luminosity, 70000), "lux"),
    ("CO2",       lambda s: s.env_state.gas_density,   (150, 1300), lambda p: p.co2_range, "ppm"),
]


def make_farm():
    sections = []
    for i, (name, temp, _, soil, hum, ec, *_) in enumerate(PROFILES):
        env = EnvState(make_profile(name), sum(temp) / 2, sum(hum) / 2, 500, sum(soil) / 2, 0, sum(ec) / 2)
        sections.append(FarmSection(env, PlantState(True, False), False, name=f"구역{i + 1}"))
    return Farm(sections, start_hour=6, profiles={p[0]: make_profile(p[0]) for p in PROFILES})


ZONES = [f"구역{i + 1}" for i in range(len(PROFILES))]
