"""센서와 센서 묶음"""
import random
from types import SimpleNamespace


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
