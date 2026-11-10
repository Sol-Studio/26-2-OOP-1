import math, random, time
from types import SimpleNamespace

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


class Readings(SimpleNamespace):
    """센서가 한 번에 읽은 값. temperature, humidity, co2, soil_humidity, nutrient, luminosity"""


class Sensor:
    """센서 베이스. 서브클래스는 measure()에서 환경의 어떤 값을 잴지만 정한다."""
    key = ""        # Readings의 속성 이름
    label = ""
    unit = ""

    def __init__(self, noise: float = 0.0):
        self.noise = noise      # 측정 오차 표준편차 (0이면 정확히 잰다)

    def measure(self, env: "EnvState") -> float:
        raise NotImplementedError

    def read(self, env: "EnvState") -> float:
        value = self.measure(env)
        return value + random.gauss(0, self.noise) if self.noise else value


class TemperatureSensor(Sensor):
    key, label, unit = "temperature", "온도", "°C"

    def measure(self, env): return env.temperature


class HumiditySensor(Sensor):
    key, label, unit = "humidity", "습도", "%"

    def measure(self, env): return env.humidity


class Co2Sensor(Sensor):
    key, label, unit = "co2", "CO2", "ppm"

    def measure(self, env): return env.gas_density


class SoilMoistureSensor(Sensor):
    key, label, unit = "soil_humidity", "토양 습도", "%"

    def measure(self, env): return env.soil_humidity


class NutrientSensor(Sensor):
    key, label, unit = "nutrient", "양액 EC", "mS/cm"

    def measure(self, env): return env.nutrient


class LightSensor(Sensor):
    key, label, unit = "luminosity", "조도", "lux"

    def measure(self, env): return env.luminosity


class SensorPanel:
    """구역에 달린 센서 모음. 장치는 환경을 직접 보지 않고 이 측정값만 본다."""
    def __init__(self, sensors=None):
        self.sensors = list(sensors) if sensors is not None else [
            TemperatureSensor(), HumiditySensor(), Co2Sensor(),
            SoilMoistureSensor(), NutrientSensor(), LightSensor()]

    def read_all(self, env: "EnvState") -> Readings:
        return Readings(**{s.key: s.read(env) for s in self.sensors})


class Effects:
    """장치들이 이번 단계에 환경에 주는 영향의 합. EnvState.update가 이 값만 본다."""
    def __init__(self):
        self.vent = 0.15            # 외기 교환율 (/h)
        self.co2_exchange = 0.2     # CO2 교환율 (/h)
        self.heat = 0.0             # °C/h
        self.humidity = 0.0         # %/h
        self.lux = 0.0
        self.water_l = 0.0
        self.fertilizer_g = 0.0


class Device:
    """장치 베이스. 환경에 주는 영향(contribute)과 자동 제어 판단(control)을 서브클래스가 정한다."""
    key = ""
    label = ""
    power_kw = 0.0          # 켜져 있을 때 소비 전력 (kW)

    @property
    def power(self) -> float:
        return 0.0

    def contribute(self, fx: Effects):
        """환경에 주는 영향을 fx에 더한다."""

    def control(self, r: Readings, profile: "PlantProfile", ctx):
        """측정값을 보고 상태를 정한다. ctx: closed(격리 중), hour, log"""

    def end_step(self):
        """한 단계가 끝날 때 1회성 상태를 비운다."""

    def reset(self):
        """식물이 없을 때: 가동을 멈춘다 (누적량은 남긴다)."""


class OnOffDevice(Device):
    """켜짐/꺼짐 장치. decide()가 (켤지, 이유)를 돌려주면 상태가 바뀔 때만 로그를 남긴다."""
    def __init__(self):
        self.on = False

    @property
    def power(self):
        return self.power_kw if self.on else 0.0

    def decide(self, r, profile, ctx):
        """(on, 이유)를 돌려준다. 상태를 유지하려면 None"""
        return None

    def control(self, r, profile, ctx):
        decision = self.decide(r, profile, ctx)
        if decision and decision[0] != self.on:
            self.on = decision[0]
            ctx.log(f"{self.label} {'ON' if self.on else 'OFF'} ({decision[1]})")

    def reset(self):
        self.on = False


class Heater(OnOffDevice):
    key, label, power_kw = "heater", "난방", 3.0

    def contribute(self, fx):
        if self.on:
            fx.heat += 4.0

    def decide(self, r, p, ctx):
        lo = p.temperature_range[0]
        if r.temperature < lo:
            return True, f"{r.temperature:.1f}°C < {lo}°C"
        if r.temperature > lo + 1:
            return False, f"{r.temperature:.1f}°C"


class Cooler(OnOffDevice):
    key, label, power_kw = "cooler", "냉방", 2.5

    def contribute(self, fx):
        if self.on:
            fx.heat -= 4.0
            fx.humidity -= 3.0      # 냉방하면 응결로 습도도 내려간다

    def decide(self, r, p, ctx):
        hi = p.temperature_range[1]
        if r.temperature > hi:
            return True, f"{r.temperature:.1f}°C > {hi}°C"
        if r.temperature < hi - 1:
            return False, f"{r.temperature:.1f}°C"


class Dehumidifier(OnOffDevice):
    key, label, power_kw = "dehumidifier", "제습기", 0.6

    def contribute(self, fx):
        if self.on:
            fx.humidity -= 12.0

    def decide(self, r, p, ctx):
        hi = p.humidity_range[1]
        if r.humidity > hi:
            return True, f"{r.humidity:.1f}% > {hi}%"
        if r.humidity < hi - 5:
            return False, f"{r.humidity:.0f}%"


class Humidifier(OnOffDevice):
    key, label, power_kw = "humidifier", "가습기", 0.4

    def contribute(self, fx):
        if self.on:
            fx.humidity += 10.0

    def decide(self, r, p, ctx):
        lo = p.humidity_range[0]
        if r.humidity < lo:
            return True, f"{r.humidity:.1f}% < {lo}%"
        if r.humidity > lo + 5:
            return False, f"{r.humidity:.0f}%"


class Fan(OnOffDevice):
    """환기: 너무 덥거나 CO2가 범위를 벗어나면 켜고, 충분히 돌아오면 끔 (격리 중엔 닫음)"""
    key, label, power_kw = "fan", "환기팬", 0.3

    def contribute(self, fx):
        if self.on:
            fx.vent += 0.8
            fx.co2_exchange += 1.5

    def decide(self, r, p, ctx):
        t_hi = p.temperature_range[1]
        c_lo, c_hi = p.co2_range
        T, C = r.temperature, r.co2
        if ctx.closed:
            return False, "격리 중"
        if T > t_hi + 2 or C > c_hi or C < c_lo:
            return True, f"{T:.1f}°C, CO2 {C:.0f}ppm"
        if T < t_hi + 1 and c_lo + 80 < C < c_hi - 100:
            return False, f"CO2 {C:.0f}ppm"


class GrowLight(Device):
    """인공조명: 6~22시 동안 자연광이 모자란 만큼 보충 (밝기 0~1)"""
    key, label = "light", "인공조명"
    KW = 1.0
    LUX = 25000

    def __init__(self):
        self.level = 0.0

    @property
    def power(self):
        return self.level * self.KW

    def contribute(self, fx):
        fx.lux += self.level * self.LUX

    def control(self, r, p, ctx):
        natural = r.luminosity - self.level * self.LUX
        if 6 <= ctx.hour < 22 and natural < p.min_luminosity:
            level = min(1.0, (p.min_luminosity - natural) / self.LUX)
        else:
            level = 0.0
        if (level > 0) != (self.level > 0):
            ctx.log(f"{self.label} {'ON' if level > 0 else 'OFF'} (자연광 {natural:,.0f}lux)")
        self.level = round(level, 2)

    def reset(self):
        self.level = 0.0


class DosingDevice(Device):
    """1회성으로 양을 투입하는 장치. amount는 이번 단계 투입량, total은 누적량"""
    def __init__(self):
        self.amount = 0.0
        self.total = 0.0

    def dose(self, amount, ctx, msg):
        self.amount = amount
        self.total += amount
        ctx.log(msg)

    def end_step(self):
        self.amount = 0.0

    def reset(self):
        self.amount = 0.0


class Irrigation(DosingDevice):
    """급수: 토양 습도가 하한 아래로 떨어지면 적정 범위 중간까지"""
    key, label = "irrigation", "급수"

    def contribute(self, fx):
        fx.water_l += self.amount

    def control(self, r, p, ctx):
        lo, hi = p.soil_humidity_range
        if r.soil_humidity < lo:
            target = (lo + hi) / 2
            liters = (target - r.soil_humidity) / 2.0
            self.dose(liters, ctx, f"급수 {liters:.1f}L (토양 습도 {r.soil_humidity:.0f}% → {target:.0f}%)")


class Fertilizer(DosingDevice):
    """비료: EC가 하한 아래면 중간값까지"""
    key, label = "fertilizer", "비료"

    def contribute(self, fx):
        fx.fertilizer_g += self.amount

    def control(self, r, p, ctx):
        lo, hi = p.nutrient_range
        if r.nutrient < lo:
            target = (lo + hi) / 2
            grams = (target - r.nutrient) / 0.02
            self.dose(grams, ctx, f"비료 {grams:.0f}g 살포 (EC {r.nutrient:.2f} → {target:.2f})")


def _device_attr(key, attr):
    return property(lambda self: getattr(self.by_key[key], attr))


class Devices:
    """구역 하나에 달린 장치들과 누적 사용량. 제어 순서대로 들고 있고, 화면용 속성도 제공한다."""
    def __init__(self, devices=None):
        self.items = list(devices) if devices is not None else [
            Heater(), Cooler(), Dehumidifier(), Humidifier(), Fan(), Irrigation(), Fertilizer(), GrowLight()]
        self.by_key = {d.key: d for d in self.items}
        self.total_energy_kwh = 0.0

    heater = _device_attr("heater", "on")
    cooler = _device_attr("cooler", "on")
    fan = _device_attr("fan", "on")
    humidifier = _device_attr("humidifier", "on")
    dehumidifier = _device_attr("dehumidifier", "on")
    light = _device_attr("light", "level")              # 인공조명 밝기 0~1
    water_l = _device_attr("irrigation", "amount")      # 이번 단계 급수량
    fertilizer_g = _device_attr("fertilizer", "amount")  # 이번 단계 비료 살포량
    total_water_l = _device_attr("irrigation", "total")
    total_fertilizer_g = _device_attr("fertilizer", "total")

    def __iter__(self):
        return iter(self.items)

    def power_kw(self):
        return sum(d.power for d in self.items)

    def effects(self) -> Effects:
        fx = Effects()
        for d in self.items:
            d.contribute(fx)
        return fx


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
        fx = dev.effects()                                 # 장치들이 주는 영향
        vent = fx.vent                                     # 외기 교환율 (/h)
        sun_in = weather.sunlight * 0.7 * (0.3 if shaded else 1.0)   # 유리 투과율, 차폐막
        self.luminosity = sun_in + fx.lux
        light = self.luminosity / 60000                    # 대략 0~1
        leaf = 1.0 if plant_alive else 0.0

        dT = ((weather.temperature - self.temperature) * vent
              + sun_in / 60000 * 3.0                       # 온실 효과
              + fx.heat)
        self.temperature += dT * dt + random.gauss(0, 0.1)

        dH = ((weather.humidity - self.humidity) * vent
              + leaf * (1 + 4 * light)                      # 증산
              + fx.humidity)
        self.humidity = min(100, max(15, self.humidity + dH * dt + random.gauss(0, 0.3)))

        dC = ((420 - self.gas_density) * fx.co2_exchange
              - leaf * 180 * light                          # 광합성
              + leaf * 25)                                  # 호흡
        self.gas_density = max(150, self.gas_density + dC * dt)

        evap = 0.5 + 0.05 * max(self.temperature, 0) + 1.5 * light * leaf
        self.soil_humidity = max(0, self.soil_humidity - evap * dt + fx.water_l * 2.0)

        uptake = leaf * (0.01 + 0.03 * light)
        self.nutrient = max(0, self.nutrient - uptake * dt - fx.water_l * 0.004 + fx.fertilizer_g * 0.02)


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

    def update(self, env: EnvState, dt: float):
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


class FarmSection:
    PEST_CONTROL_RATE = 0.25      # 격리 중 시간당 방제 시도 확률
    PEST_CONTROL_SUCCESS = 0.7    # 방제 한 번이 성공할 확률
    PLOW_HINT_FAILURES = 3        # 이만큼 연속 실패하면 갈아엎기를 권한다

    def __init__(self, env_state: EnvState, plant_state: PlantState, is_closed: bool, name: str = ""):
        self.env_state = env_state
        self.plant_state = plant_state    # 빈 구역이면 None
        self.is_closed = is_closed
        self.devices = Devices()
        self.sensors = SensorPanel()
        self.name = name
        self.control_failures = 0         # 이번 병충해에 대한 연속 방제 실패 횟수
        self.base_usage = (0.0, 0.0, 0.0)  # 이번 재배를 시작할 때의 누적 (전력 kWh, 물 L, 비료 g)
        self.cycles = []                  # 끝난 재배 기록 (비용·수익 계산용)

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
        self.base_usage = self._total_usage()
        self.plant_state = PlantState()
        self.log(f"파종 (예상 {profile.grow_days:g}일 후 수확)")
        return True

    def _total_usage(self):
        d = self.devices
        return (d.total_energy_kwh, d.total_water_l, d.total_fertilizer_g)

    def cycle_usage(self):
        """이번 재배에 쓴 (전력 kWh, 물 L, 비료 g)"""
        return tuple(now - base for now, base in zip(self._total_usage(), self.base_usage))

    def _close(self, outcome: str, kg: float = 0.0, quality: float = 0.0):
        """재배를 끝내며 사용량과 결과를 기록하고 구역을 비운다."""
        kwh, water, fert = self.cycle_usage()
        self.cycles.append(dict(species=self.env_state.plant_profile.species, outcome=outcome, kg=kg,
                                quality=quality, kwh=kwh, water_l=water, fertilizer_g=fert,
                                days=self.plant_state.age_hours / 24))
        self._clear()

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
        self._close("갈아엎음")
        return True

    def harvest(self):
        """다 자랐으면 수확해서 (작물, 수확량 kg, 품질 %)를 돌려준다. 고사한 작물은 정리만 한다."""
        plant, p = self.plant_state, self.env_state.plant_profile
        if plant is None:
            self.log("수확할 작물이 없습니다.")
            return None
        if not plant.alive:
            self.log("고사한 작물을 정리했습니다.")
            self._close("고사")
            return None
        if not plant.ready:
            self.log(f"아직 수확할 수 없습니다 ({p.stage(plant.growth)}, 생장 {plant.growth:.0f}%).")
            return None
        quality = plant.avg_health
        kg = p.yield_kg * quality / 100
        self.log(f"수확 {kg:.1f}kg (품질 {quality:.0f}%, 재배 {plant.age_hours / 24:.1f}일)")
        self._close("수확", kg, quality)
        return p.species, kg, quality

    def process(self, weather: Weather = None, hour: float = 12.0, dt: float = 1 / 6):
        """dt시간만큼 환경·식물을 진행시키고, 센서 측정값으로 장치를 조절한다."""
        was_alive = self._advance(weather or Weather(), dt)
        if not (self.plant_state and self.plant_state.alive):
            self._shutdown(was_alive)
            return
        self._handle_pests(dt)
        self._run_controls(hour)

    def _advance(self, weather: Weather, dt: float) -> bool:
        """환경과 식물을 dt만큼 진행한다. 진행 전에 식물이 살아 있었는지 돌려준다."""
        env, plant, dev = self.env_state, self.plant_state, self.devices
        was_alive = bool(plant and plant.alive)
        env.update(weather, dev, was_alive, self.is_closed, dt)
        if plant:
            p = env.plant_profile
            stage = p.stage(plant.growth)
            plant.update(env, dt)
            if plant.alive and p.stage(plant.growth) != stage:
                self.log(f"생육 단계 {stage} → {p.stage(plant.growth)}" + (" · 수확 가능" if plant.ready else ""))
        dev.total_energy_kwh += dev.power_kw() * dt
        for d in dev:
            d.end_step()
        return was_alive

    def _shutdown(self, was_alive: bool):
        """빈 구역이거나 고사했으면 장치를 모두 끈다."""
        if was_alive:
            self.log("식물이 죽었습니다.")
        for d in self.devices:
            d.reset()

    def _handle_pests(self, dt: float):
        """병충해: 구역 차폐 후 방제(일정 확률로 실패), 사라지면 개방"""
        plant = self.plant_state
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

    def _run_controls(self, hour: float):
        """센서를 한 번 읽고, 각 장치가 스스로 켜고 끌지 판단한다."""
        readings = self.sensors.read_all(self.env_state)
        ctx = SimpleNamespace(closed=self.is_closed, hour=hour, log=self.log)
        for d in self.devices:
            d.control(readings, self.env_state.plant_profile, ctx)


class Farm:
    def __init__(self, sections: list, start_hour: float = 6.0, weather: Weather = None,
                 auto_harvest: bool = True):
        self.sections = sections
        self.auto_harvest = auto_harvest   # 다 자란 구역을 바로 수확한다
        self.hours = start_hour      # 시뮬레이션 시작부터 흐른 시간
        self.weather = weather or Weather()
        self.harvests = []           # (일차, 구역 이름, 작물, kg, 품질 %)

    @property
    def cycles(self):
        """모든 구역의 끝난 재배 기록"""
        return [c for s in self.sections for c in s.cycles]

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
            if self.auto_harvest and section.plant_state and section.plant_state.ready:
                self.harvest(section)


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
