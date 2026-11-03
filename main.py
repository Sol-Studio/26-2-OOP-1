import math, random, time

# 생육 단계: (이름, 시작 생장도). 마지막 단계에 도달하면 수확할 수 있다.
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


class Weather:
    """바깥 날씨. 하루 주기로 기온·일사량·습도가 변하고, 구름이 무작위로 낀다."""
    def __init__(self, base_temp=12.0, temp_swing=7.0):
        self.base_temp = base_temp
        self.temp_swing = temp_swing
        self.cloud = 0.2
        self.temperature = base_temp
        self.humidity = 70.0
        self.sunlight = 0.0

    def update(self, hour: float, dt: float):
        self.cloud = min(0.9, max(0.0, self.cloud + random.gauss(0, 0.15) * math.sqrt(dt)))
        # 최저기온 새벽 3시, 최고기온 오후 3시
        self.temperature = self.base_temp + self.temp_swing * math.sin(2 * math.pi * (hour - 9) / 24)
        sun = max(0.0, math.sin(math.pi * (hour - 6) / 12))   # 6시 일출, 18시 일몰
        self.sunlight = 80000 * sun * (1 - 0.7 * self.cloud)
        self.humidity = min(98, max(30, 75 - (self.temperature - self.base_temp) * 3 + self.cloud * 15))


class Devices:
    """구역 하나에 달린 장치들과 누적 사용량"""
    POWER_KW = {"heater": 3.0, "cooler": 2.5, "fan": 0.3, "humidifier": 0.4, "dehumidifier": 0.6}
    LIGHT_KW = 1.0
    LIGHT_LUX = 25000

    def __init__(self):
        self.heater = self.cooler = self.fan = False
        self.humidifier = self.dehumidifier = False
        self.light = 0.0          # 인공조명 밝기 0~1
        self.water_l = 0.0        # 이번 단계 급수량
        self.fertilizer_g = 0.0   # 이번 단계 비료 살포량
        self.total_water_l = 0.0
        self.total_fertilizer_g = 0.0
        self.total_energy_kwh = 0.0

    def power_kw(self):
        kw = sum(p for name, p in self.POWER_KW.items() if getattr(self, name))
        return kw + self.light * self.LIGHT_KW


class EnvState:
    def __init__(self, plant_profile: PlantProfile, temperature: float, humidity: float,
                 gas_density: float, soil_humidity: float, luminosity: float, nutrient: float = 1.5):
        self.plant_profile = plant_profile
        self.temperature = temperature
        self.humidity = humidity
        self.gas_density = gas_density      # CO2 농도 (ppm)
        self.soil_humidity = soil_humidity
        self.luminosity = luminosity
        self.nutrient = nutrient            # 양액 EC (mS/cm)

    def update(self, weather: Weather, dev: Devices, plant_alive: bool, shaded: bool, dt: float):
        """dt시간 동안의 온실 내부 환경 변화"""
        vent = 0.15 + 0.8 * dev.fan                        # 외기 교환율 (/h)
        sun_in = weather.sunlight * 0.7 * (0.3 if shaded else 1.0)   # 유리 투과율, 차폐막
        self.luminosity = sun_in + dev.light * Devices.LIGHT_LUX
        light = self.luminosity / 60000                    # 대략 0~1
        leaf = 1.0 if plant_alive else 0.0

        dT = ((weather.temperature - self.temperature) * vent
              + sun_in / 60000 * 3.0                       # 온실 효과
              + 4.0 * dev.heater - 4.0 * dev.cooler)
        self.temperature += dT * dt + random.gauss(0, 0.1)

        dH = ((weather.humidity - self.humidity) * vent
              + leaf * (1 + 4 * light)                      # 증산
              + 10 * dev.humidifier - 12 * dev.dehumidifier - 3 * dev.cooler)
        self.humidity = min(100, max(15, self.humidity + dH * dt + random.gauss(0, 0.3)))

        dC = ((420 - self.gas_density) * (0.2 + 1.5 * dev.fan)
              - leaf * 180 * light                          # 광합성
              + leaf * 25)                                  # 호흡
        self.gas_density = max(150, self.gas_density + dC * dt)

        evap = 0.5 + 0.05 * max(self.temperature, 0) + 1.5 * light * leaf
        self.soil_humidity = max(0, self.soil_humidity - evap * dt + dev.water_l * 2.0)

        uptake = leaf * (0.01 + 0.03 * light)
        self.nutrient = max(0, self.nutrient - uptake * dt - dev.water_l * 0.004 + dev.fertilizer_g * 0.02)


class PlantState:
    OVERRIPE_STRESS = 0.3   # 수확기를 넘기면 조금씩 상한다

    def __init__(self, alive: bool = True, pests: bool = False, health: float = 100.0, growth: float = 0.0):
        self.alive = alive
        self.pests = pests
        self.health = health    # 0이 되면 고사
        self.growth = growth    # 수확까지 0~100
        self.age_hours = 0.0    # 파종 후 경과 시간
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

    def update(self, env: EnvState, dt: float):
        if not self.alive:
            return
        p = env.plant_profile
        self.age_hours += dt
        stress = self.OVERRIPE_STRESS if self.ready else 0.0
        stress += _out_of(env.temperature, p.temperature_range) / 3
        stress += _out_of(env.humidity, p.humidity_range) / 15
        stress += _out_of(env.soil_humidity, p.soil_humidity_range) / 10
        stress += _out_of(env.nutrient, p.nutrient_range) / 0.5
        if self.pests:
            stress += 1.5
        self.health += (1.0 - 3.0 * stress) * dt
        self.health = min(100.0, self.health)
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


class FarmSection:
    PEST_CONTROL_RATE = 0.25      # 격리 중 시간당 방제 시도 확률
    PEST_CONTROL_SUCCESS = 0.7    # 방제 한 번이 성공할 확률
    PLOW_HINT_FAILURES = 3        # 이만큼 연속 실패하면 갈아엎기를 권한다

    def __init__(self, env_state: EnvState, plant_state: PlantState, is_closed: bool, name: str = ""):
        self.env_state = env_state
        self.plant_state = plant_state    # 빈 구역이면 None
        self.is_closed = is_closed
        self.devices = Devices()
        self.name = name
        self.control_failures = 0         # 이번 병충해에 대한 연속 방제 실패 횟수

    @property
    def label(self):
        crop = self.env_state.plant_profile.species if self.plant_state else "빈 구역"
        return f"{self.name} {crop}" if self.name else crop

    def log(self, msg):
        print(f"[{self.label}] {msg}")

    def plant(self, profile: PlantProfile) -> bool:
        """빈 구역에 작물을 심는다. 작물이 남아 있으면 심지 않는다."""
        if self.plant_state:
            self.log("작물이 남아 있어 심을 수 없습니다. 먼저 수확하거나 정리하세요.")
            return False
        self.env_state.plant_profile = profile
        self._clear()
        self.plant_state = PlantState()
        self.log(f"파종 (예상 {profile.grow_days:g}일 후 수확)")
        return True

    def _clear(self):
        self.plant_state = None
        self.is_closed = False
        self.control_failures = 0

    def plow(self) -> bool:
        """자라는 중이든 병들었든 작물을 모두 갈아엎어 빈 구역으로 만든다. 수확량은 없다."""
        plant, p = self.plant_state, self.env_state.plant_profile
        if plant is None:
            self.log("갈아엎을 작물이 없습니다.")
            return False
        state = "고사" if not plant.alive else f"{p.stage(plant.growth)} {plant.growth:.0f}%"
        self.log(f"밭을 갈아엎었습니다 ({state}" + (", 병충해 제거" if plant.pests else "") + ").")
        self._clear()
        return True

    def harvest(self):
        """다 자랐으면 수확해서 (작물, 수확량 kg, 품질 %)를 돌려준다. 고사한 작물은 정리만 한다."""
        plant, p = self.plant_state, self.env_state.plant_profile
        if plant is None:
            self.log("수확할 작물이 없습니다.")
            return None
        if not plant.alive:
            self.log("고사한 작물을 정리했습니다.")
            self._clear()
            return None
        if not plant.ready:
            self.log(f"아직 수확할 수 없습니다 ({p.stage(plant.growth)}, 생장 {plant.growth:.0f}%).")
            return None
        quality = plant.avg_health
        kg = p.yield_kg * quality / 100
        self.log(f"수확 {kg:.1f}kg (품질 {quality:.0f}%, 재배 {plant.age_hours / 24:.1f}일)")
        self._clear()
        return p.species, kg, quality

    def switch(self, device: str, on: bool, reason: str):
        if getattr(self.devices, device) != on:
            setattr(self.devices, device, on)
            label = {"heater": "난방", "cooler": "냉방", "fan": "환기팬",
                     "humidifier": "가습기", "dehumidifier": "제습기"}[device]
            self.log(f"{label} {'ON' if on else 'OFF'} ({reason})")

    def process(self, weather: Weather = None, hour: float = 12.0, dt: float = 1 / 6):
        """dt시간만큼 환경·식물을 진행시키고, 측정값을 보고 장치를 조절한다."""
        env, plant, dev, p = self.env_state, self.plant_state, self.devices, self.env_state.plant_profile
        weather = weather or Weather()

        was_alive = bool(plant and plant.alive)
        env.update(weather, dev, was_alive, self.is_closed, dt)
        if plant:
            stage = p.stage(plant.growth)
            plant.update(env, dt)
            if plant.alive and p.stage(plant.growth) != stage:
                self.log(f"생육 단계 {stage} → {p.stage(plant.growth)}" + (" · 수확 가능" if plant.ready else ""))
        dev.total_energy_kwh += dev.power_kw() * dt
        dev.water_l = dev.fertilizer_g = 0.0

        # 빈 구역이거나 고사했으면 장치를 모두 끈다
        if not (plant and plant.alive):
            if was_alive:
                self.log("식물이 죽었습니다.")
            for d in ("heater", "cooler", "fan", "humidifier", "dehumidifier"):
                setattr(dev, d, False)
            dev.light = 0.0
            return

        # 병충해: 구역 차폐 후 방제(일정 확률로 실패), 사라지면 개방
        if plant.pests and not self.is_closed:
            self.log("병충해 발생이 감지되어 구역을 격리합니다.")
            self.is_closed = True
        elif self.is_closed and plant.pests and random.random() < self.PEST_CONTROL_RATE * dt:
            if random.random() < self.PEST_CONTROL_SUCCESS:
                plant.pests = False
            else:
                self.control_failures += 1
                hint = " 갈아엎기를 고려하세요." if self.control_failures >= self.PLOW_HINT_FAILURES else ""
                self.log(f"방제 실패 ({self.control_failures}회째), 격리를 유지하고 다시 방제합니다.{hint}")
        if self.is_closed and not plant.pests:
            self.log("방제 완료, 구역 격리를 해제합니다.")
            self.is_closed = False
            self.control_failures = 0

        # 냉난방 (1°C 히스테리시스)
        t_lo, t_hi = p.temperature_range
        T = env.temperature
        if T < t_lo:
            self.switch("heater", True, f"{T:.1f}°C < {t_lo}°C")
        elif T > t_lo + 1:
            self.switch("heater", False, f"{T:.1f}°C")
        if T > t_hi:
            self.switch("cooler", True, f"{T:.1f}°C > {t_hi}°C")
        elif T < t_hi - 1:
            self.switch("cooler", False, f"{T:.1f}°C")

        # 습도
        h_lo, h_hi = p.humidity_range
        H = env.humidity
        if H > h_hi:
            self.switch("dehumidifier", True, f"{H:.1f}% > {h_hi}%")
        elif H < h_hi - 5:
            self.switch("dehumidifier", False, f"{H:.0f}%")
        if H < h_lo:
            self.switch("humidifier", True, f"{H:.1f}% < {h_lo}%")
        elif H > h_lo + 5:
            self.switch("humidifier", False, f"{H:.0f}%")

        # 환기: 너무 덥거나 CO2가 범위를 벗어나면 켜고, 충분히 돌아오면 끔 (격리 중엔 닫음)
        c_lo, c_hi = p.co2_range
        C = env.gas_density
        if self.is_closed:
            self.switch("fan", False, "격리 중")
        elif T > t_hi + 2 or C > c_hi or C < c_lo:
            self.switch("fan", True, f"{T:.1f}°C, CO2 {C:.0f}ppm")
        elif T < t_hi + 1 and c_lo + 80 < C < c_hi - 100:
            self.switch("fan", False, f"CO2 {C:.0f}ppm")

        # 급수: 하한 아래로 떨어지면 적정 범위 중간까지
        s_lo, s_hi = p.soil_humidity_range
        if env.soil_humidity < s_lo:
            target = (s_lo + s_hi) / 2
            dev.water_l = (target - env.soil_humidity) / 2.0
            dev.total_water_l += dev.water_l
            self.log(f"급수 {dev.water_l:.1f}L (토양 습도 {env.soil_humidity:.0f}% → {target:.0f}%)")

        # 비료: EC가 하한 아래면 중간값까지
        n_lo, n_hi = p.nutrient_range
        if env.nutrient < n_lo:
            target = (n_lo + n_hi) / 2
            dev.fertilizer_g = (target - env.nutrient) / 0.02
            dev.total_fertilizer_g += dev.fertilizer_g
            self.log(f"비료 {dev.fertilizer_g:.0f}g 살포 (EC {env.nutrient:.2f} → {target:.2f})")

        # 인공조명: 6~22시 동안 자연광이 모자란 만큼 보충
        natural = env.luminosity - dev.light * Devices.LIGHT_LUX
        if 6 <= hour < 22 and natural < p.min_luminosity:
            level = min(1.0, (p.min_luminosity - natural) / Devices.LIGHT_LUX)
        else:
            level = 0.0
        if (level > 0) != (dev.light > 0):
            self.log(f"인공조명 {'ON' if level > 0 else 'OFF'} (자연광 {natural:,.0f}lux)")
        dev.light = round(level, 2)


class Farm:
    def __init__(self, sections: list, start_hour: float = 6.0, weather: Weather = None):
        self.sections = sections
        self.hours = start_hour      # 시뮬레이션 시작부터 흐른 시간
        self.weather = weather or Weather()
        self.harvests = []           # (일차, 구역 이름, 작물, kg, 품질 %)

    @property
    def hour(self):
        return self.hours % 24

    @property
    def day(self):
        return int(self.hours // 24) + 1

    def harvest(self, section: FarmSection):
        result = section.harvest()
        if result:
            self.harvests.append((self.day, section.name, *result))
        return result

    def process(self, dt: float = 1 / 6):
        self.hours += dt
        self.weather.update(self.hour, dt)
        for section in self.sections:
            section.process(self.weather, self.hour, dt)


if __name__ == "__main__":
    lettuce = PlantProfile("상추", (15, 22), 15000, (55, 75), humidity_range=(60, 80), nutrient_range=(1.0, 1.6),
                           grow_days=6, yield_kg=4.0)
    section1 = FarmSection(EnvState(lettuce, 17, 47, 600, 30, 30000), PlantState(True, False), False)
    farm = Farm([section1])
    while True:
        time.sleep(0.1)
        farm.process()      # 한 번에 10분 진행
        if not (section1.plant_state.alive and not section1.plant_state.ready):
            farm.harvest(section1)      # 다 자랐거나 죽었으면 수확·정리하고 다시 심는다
            section1.plant(lettuce)
        e, plant = section1.env_state, section1.plant_state
        print(f"  Day{farm.day} {farm.hour:05.2f}h  {e.temperature:5.1f}°C  {e.humidity:4.0f}%  "
              f"토양 {e.soil_humidity:4.0f}%  EC {e.nutrient:.2f}  {e.luminosity:7,.0f}lux  "
              f"건강 {plant.health:5.1f}  {lettuce.stage(plant.growth)} {plant.growth:3.0f}%")
