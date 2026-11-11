"""바깥 날씨"""
import math, random


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
