"""냉난방·환기·조명·급수·비료 장치"""
from core.plant import PlantProfile
from core.sensors import Readings


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

    def control(self, r: Readings, profile: PlantProfile, ctx):
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
