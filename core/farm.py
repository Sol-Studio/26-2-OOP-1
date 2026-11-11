"""농장 전체: 구역, 날씨, 시세, 수확 기록"""
from core import economics
from core.market import Market
from core.section import FarmSection
from core.weather import Weather


class Farm:
    def __init__(self, sections: list, start_hour: float = 6.0, weather: Weather = None,
                 auto_harvest: bool = True, market: Market = None, profiles: dict = None):
        self.sections = sections
        self.auto_harvest = auto_harvest   # 다 자란 구역을 바로 수확한다
        self.hours = start_hour      # 시뮬레이션 시작부터 흐른 시간
        self.weather = weather or Weather()
        self.harvests = []           # (일차, 구역 이름, 작물, kg, 품질 %, 수확 때 시세)
        self.market = market or Market({name: p[0] for name, p in economics.PRICES.items()})
        self.profiles = profiles or {}     # 자동 재파종 후보: {작물 이름: PlantProfile}
        self.auto_replant = False          # 수확한 구역에 가장 효율 좋은 작물을 다시 심는다

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
            species, kg, _ = result
            self.market.ensure(species, economics.base_price(species))
            price = self.market.price(species)
            section.cycles[-1]["price"] = price
            self.market.sell(species, kg)
            self.harvests.append((self.day, section.name, *result, price))
            if self.auto_replant and self.profiles:
                self.replant(section)
        return result

    def replant(self, section: FarmSection):
        """지금 시세 기준으로 하루당 순이익이 가장 큰 작물을 빈 구역에 심는다."""
        prices = {name: self.market.price(name) for name in self.profiles}
        name = economics.best_crop(self.profiles, prices, self.cycles)
        section.plant(self.profiles[name])
        section.log(f"자동 재파종: 시세 {prices[name]:,.0f}원/kg인 {name} 선택")

    def process(self, dt: float = 1 / 6):
        self.hours += dt
        self.weather.update(self.hour, dt)
        self.market.step(dt)
        for section in self.sections:
            section.process(self.weather, self.hour, dt)
            if self.auto_harvest and section.plant_state and section.plant_state.ready:
                self.harvest(section)
