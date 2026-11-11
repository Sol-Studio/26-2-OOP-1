"""작물 정보(적정 조건)와 식물의 생육 상태"""
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.environment import EnvState

LEAFY_STAGES = (("발아", 0), ("유묘", 10), ("생장", 35), ("수확기", 100))
FRUIT_STAGES = (("발아", 0), ("유묘", 10), ("영양생장", 30), ("개화", 55), ("결실", 75), ("수확기", 100))


class PlantProfile:
    """작물별 적정 생육 조건"""
    def __init__(self, species: str, temperature_range: tuple, min_luminosity: float,
                 soil_humidity_range: tuple, humidity_range: tuple = (60, 80),
                 nutrient_range: tuple = (1.0, 2.0), co2_range: tuple = (300, 1200),
                 grow_days: float = 8, yield_kg: float = 5.0, stages: tuple = LEAFY_STAGES):
        self.species = species
        self.temperature_range = temperature_range      # °C
        self.min_luminosity = min_luminosity            # lux
        self.soil_humidity_range = soil_humidity_range  # %
        self.humidity_range = humidity_range            # %RH
        self.nutrient_range = nutrient_range            # 양액 EC (mS/cm)
        self.co2_range = co2_range                      # ppm
        self.grow_days = grow_days                      # 조건이 좋을 때 파종부터 수확까지 (일)
        self.yield_kg = yield_kg                        # 건강도 100으로 키웠을 때 구역 수확량
        self.stages = stages

    def stage(self, growth: float) -> str:
        return [name for name, start in self.stages if growth >= start][-1]


class PlantState:
    OVERRIPE_DECAY = 1.0    # 수확기를 넘기면 시간당 이만큼 건강도가 떨어진다 (회복과 무관)

    def __init__(self, alive: bool = True, pests: bool = False, health: float = 100.0, growth: float = 0.0):
        self.alive = alive
        self.pests = pests
        self.health = health    # 0이 되면 고사
        self.growth = growth    # 수확까지 0~100
        self.age_hours = 0.0    # 파종 후 경과 시간
        self.overripe_hours = 0.0  # 수확기를 넘긴 뒤 경과 시간
        self.health_hours = 0.0 # 건강도 × 시간 누적 (평균 건강도 = 품질)

    @property
    def ready(self):
        return self.alive and self.growth >= 100

    @property
    def avg_health(self):
        return self.health_hours / self.age_hours if self.age_hours else self.health

    def hours_to_harvest(self):
        """지금까지의 평균 생장 속도로 본 남은 시간. 아직 모르면 None"""
        if self.growth >= 100:
            return 0.0
        if self.growth <= 0 or self.age_hours < 1:
            return None
        return (100 - self.growth) / (self.growth / self.age_hours)

    def update(self, env: "EnvState", dt: float):
        if not self.alive:
            return
        p = env.plant_profile
        self.age_hours += dt
        stress = _out_of(env.temperature, p.temperature_range) / 3
        stress += _out_of(env.humidity, p.humidity_range) / 15
        stress += _out_of(env.soil_humidity, p.soil_humidity_range) / 10
        stress += _out_of(env.nutrient, p.nutrient_range) / 0.5
        if self.pests:
            stress += 1.5
        delta = (1.0 - 3.0 * stress) * dt
        if self.ready:
            # 수확기를 넘기면 회복하지 못하고, 환경이 좋아도 계속 상한다
            self.overripe_hours += dt
            delta = min(delta, 0.0) - self.OVERRIPE_DECAY * dt
        self.health = min(100.0, self.health + delta)
        if self.health <= 0:
            self.health = 0
            self.alive = False
            return
        self.health_hours += self.health * dt
        # 하루 16시간 빛을 받는다고 보고 grow_days 만에 다 자라도록
        light = min(1.0, env.luminosity / p.min_luminosity)
        rate = 100 / (p.grow_days * 16)
        self.growth = min(100.0, self.growth + rate * light * (self.health / 100) * dt)

        # 덥고 습하면 병충해가 잘 생긴다
        rate = 0.003 + (0.03 if env.humidity > 85 and env.temperature > 22 else 0)
        if not self.pests and random.random() < rate * dt:
            self.pests = True


def _out_of(value, rng):
    lo, hi = rng
    return lo - value if value < lo else value - hi if value > hi else 0.0
