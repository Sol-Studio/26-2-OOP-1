"""구역 안의 온도·습도·토양·양액·조도 변화"""
import random

from core.devices import Devices
from core.weather import Weather
from core.plant import PlantProfile


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
