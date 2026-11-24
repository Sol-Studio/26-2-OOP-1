"""바깥 날씨"""
import math, random

YEAR_DAYS = 120         # 시뮬레이션의 1년 (계절 하나 = 30일). 시연하기 좋게 실제보다 줄였다.
# 계절: (이름, 1년 중 한가운데 위치 0~1). 봄 한가운데에서 시작한다.
SEASONS = [("봄", 0.0), ("여름", 0.25), ("가을", 0.5), ("겨울", 0.75)]


class Weather:
    """바깥 날씨. 하루 주기로 기온·일사량·습도가 변하고, 구름이 무작위로 낀다.
    seasons를 켜면 계절에 따라 평균 기온(±season_swing)과 낮 길이(12±2시간)도 바뀐다."""
    def __init__(self, base_temp=12.0, temp_swing=7.0, seasons=False, season_swing=10.0):
        self.base_temp = base_temp
        self.temp_swing = temp_swing
        self.seasons = seasons
        self.season_swing = season_swing
        self.day_offset = 0.0       # 계절 건너뛰기용 (일)
        self.phase = 0.0            # 1년 중 위치 0~1 (0 = 봄 한가운데)
        self.cloud = 0.2
        self.temperature = base_temp
        self.humidity = 70.0
        self.sunlight = 0.0

    @property
    def season(self):
        """지금 계절 이름. 계절을 끄면 None"""
        if not self.seasons:
            return None
        gap = lambda center: min(abs(self.phase - center), 1 - abs(self.phase - center))
        return min(SEASONS, key=lambda s: gap(s[1]))[0]

    def jump_to(self, season, day):
        """지금(day일차)이 그 계절 한가운데가 되도록 달력을 옮긴다."""
        center = dict(SEASONS)[season]
        self.day_offset = (center * YEAR_DAYS - (day - 1)) % YEAR_DAYS
        self.phase = center

    def update(self, hour: float, dt: float, day: float = None):
        """day: 시작부터 흐른 날 (1일차 0시 = 1.0). 계절을 켰을 때만 쓴다."""
        s = 0.0                                             # 계절 세기: 여름 +1, 겨울 -1
        if self.seasons and day is not None:
            self.phase = ((day - 1 + self.day_offset) / YEAR_DAYS) % 1
            s = math.sin(2 * math.pi * self.phase)
        half = 6 + 2 * s                                    # 낮 길이의 절반 (시간)
        self.cloud = min(0.9, max(0.0, self.cloud + random.gauss(0, 0.15) * math.sqrt(dt)))
        # 최저기온 새벽 3시, 최고기온 오후 3시
        base = self.base_temp + self.season_swing * s
        self.temperature = base + self.temp_swing * math.sin(2 * math.pi * (hour - 9) / 24)
        sun = max(0.0, math.sin(math.pi * (hour - (12 - half)) / (2 * half)))   # 일출 12-half시, 일몰 12+half시
        self.sunlight = 80000 * (1 + 0.15 * s) * sun * (1 - 0.7 * self.cloud)
        self.humidity = min(98, max(30, 75 - (self.temperature - base) * 3 + self.cloud * 15))
