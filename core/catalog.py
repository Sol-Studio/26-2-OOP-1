"""작물 목록과 기본 농장 만들기"""
from core.environment import EnvState
from core.farm import Farm
from core.plant import PlantProfile, PlantState, LEAFY_STAGES, FRUIT_STAGES
from core.section import FarmSection

DT = 1 / 6              # 한 단계 = 10분

# 작물, 적정 온도, 최소 조도, 적정 토양 습도, 적정 습도, 적정 EC, 재배 일수, 수확량(kg), 생육 단계
PROFILES = [
    ("상추",     (15, 22), 15000, (55, 75), (60, 80), (1.0, 1.6), 6,  120.0,  LEAFY_STAGES),
    ("토마토",   (18, 27), 30000, (60, 80), (60, 80), (2.0, 3.5), 12, 360.0, FRUIT_STAGES),
    ("딸기",     (17, 25), 25000, (55, 75), (60, 75), (0.8, 1.4), 10, 150.0, FRUIT_STAGES),
    ("파프리카", (20, 27), 30000, (60, 80), (60, 80), (2.0, 3.0), 12, 300.0, FRUIT_STAGES),
    ("오이",     (20, 28), 25000, (65, 85), (70, 90), (1.8, 2.5), 8,  450.0, FRUIT_STAGES),
    ("시금치",   (15, 20), 15000, (55, 75), (60, 80), (1.5, 2.0), 6,  90.0,  LEAFY_STAGES),
]

ZONES = [f"구역{i + 1}" for i in range(len(PROFILES))]


def make_profile(name):
    _, temp, lux, soil, hum, ec, days, kg, stages = next(p for p in PROFILES if p[0] == name)
    return PlantProfile(name, temp, lux, soil, humidity_range=hum, nutrient_range=ec,
                        grow_days=days, yield_kg=kg, stages=stages)


def make_farm():
    sections = []
    for i, (name, temp, _, soil, hum, ec, *_) in enumerate(PROFILES):
        env = EnvState(make_profile(name), sum(temp) / 2, sum(hum) / 2, 500, sum(soil) / 2, 0, sum(ec) / 2)
        sections.append(FarmSection(env, PlantState(True, False), False, name=f"구역{i + 1}"))
    return Farm(sections, start_hour=6, profiles={p[0]: make_profile(p[0]) for p in PROFILES})
