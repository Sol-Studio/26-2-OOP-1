"""작물 시세. 기준가를 중심으로 랜덤하게 오르내리고, 많이 팔면 그 작물 시세가 눌린다."""
import math, random
from collections import deque

HISTORY_DAYS = 30
MIN_RATIO, MAX_RATIO = 0.5, 1.8     # 기준가 대비 시세가 움직일 수 있는 범위
HALF_LIFE_H = 72                    # 기준가로 되돌아오는 반감기 (시간)
VOLATILITY = 0.028                  # 시세 변동폭 (시간 제곱근당 로그 변화)
SELL_IMPACT = 0.03                  # 100kg을 팔 때 떨어지는 로그 시세


class Market:
    def __init__(self, base_prices: dict, steps_per_day: int = 144):
        self.base = dict(base_prices)
        self.x = {name: 0.0 for name in self.base}       # 기준가 대비 로그 시세
        self.history = {name: deque(maxlen=HISTORY_DAYS * steps_per_day) for name in self.base}
        self.record()

    def ensure(self, species, base):
        """목록에 없는 작물이면 기준가 base로 새로 등록한다."""
        if species not in self.base:
            self.base[species] = base
            self.x[species] = 0.0
            self.history[species] = deque([base], maxlen=self.history[next(iter(self.history))].maxlen)

    def price(self, species):
        return self.base[species] * math.exp(self.x[species])

    def ratio(self, species):
        return math.exp(self.x[species])

    def record(self):
        for name in self.base:
            self.history[name].append(self.price(name))

    def step(self, dt: float):
        """dt시간이 흐른다: 기준가로 되돌아오면서 무작위로 흔들린다."""
        k = math.log(2) / HALF_LIFE_H
        lo, hi = math.log(MIN_RATIO), math.log(MAX_RATIO)
        for name in self.x:
            x = self.x[name] - k * self.x[name] * dt + VOLATILITY * math.sqrt(dt) * random.gauss(0, 1)
            self.x[name] = min(hi, max(lo, x))
        self.record()

    def sell(self, species, kg: float):
        """kg를 팔면 그 작물 시세가 내려간다."""
        self.x[species] = max(math.log(MIN_RATIO), self.x[species] - SELL_IMPACT * kg / 100)
