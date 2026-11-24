"""화면 없이 농장 시뮬레이션을 돌리는 서버 쪽 상태.
예전 tkinter 관리 패널(App)이 하던 일 — 시간 진행, 그래프 기록, 로그 수집, 사람의 조작 — 을 여기서 한다.
core/는 그대로 쓰고, 화면(웹)은 snapshot()과 sync()가 돌려주는 JSON만 본다."""
import asyncio
import contextlib
import io
import itertools
import re
from collections import deque

from core import economics
from core.catalog import DT, PROFILES, ZONES, make_farm, make_profile
from core.devices import Devices
from core.economics import cycle_result, section_money, totals
from core.weather import SEASONS, YEAR_DAYS

HISTORY = 6 * 24            # 그래프에 남길 단계 수 (24시간)
LOG_MAX = 3000
LEDGER_DAYS = 30            # 일별 정산을 남길 날 수
STEPS_PER_DAY = 144
SPEED_RANGE = (20, 1000)    # 10분 진행 간격 (ms)
DEFAULT_SPEED = 167         # 1초에 1시간
WARN_WORDS = ("병충해", "죽었", "격리", "없습니다", "실패", "갈아엎")
GOOD_WORDS = ("완료", "해제")
WEATHER = [("평년", 0), ("한파", -10), ("폭염", 12)]
CROPS = [p[0] for p in PROFILES]

# 그래프: (키, 제목, y축 범위, 단위, 값 꺼내는 함수, 적정 범위 함수)
METRICS = [
    ("temperature", "온도",      (0, 40),     "°C",    lambda e: e.temperature,   lambda p: p.temperature_range),
    ("humidity",    "습도",      (20, 100),   "%",     lambda e: e.humidity,      lambda p: p.humidity_range),
    ("soil",        "토양 습도", (0, 100),    "%",     lambda e: e.soil_humidity, lambda p: p.soil_humidity_range),
    ("nutrient",    "양액 EC",   (0, 4),      "mS/cm", lambda e: e.nutrient,      lambda p: p.nutrient_range),
    ("luminosity",  "조도",      (0, 70000),  "lux",   lambda e: e.luminosity,    lambda p: (p.min_luminosity, 70000)),
    ("co2",         "CO2",       (150, 1300), "ppm",   lambda e: e.gas_density,   lambda p: p.co2_range),
]
# 관리자가 고칠 수 있는 작물 적정 조건: 그래프 키 → PlantProfile 속성 (조도는 하한 하나)
PROFILE_FIELDS = {"temperature": "temperature_range", "humidity": "humidity_range", "soil": "soil_humidity_range",
                  "nutrient": "nutrient_range", "co2": "co2_range", "luminosity": "min_luminosity"}
METRIC_RANGE = {key: rng for key, _, rng, *_ in METRICS}


def section_status(s):
    """구역 상태 글과 색 이름 (웹에서 색으로 바꾼다)"""
    if not s.plant_state:
        return "파종 대기", "muted"
    if not s.plant_state.alive:
        return "고사", "dead"
    if s.is_closed:
        if s.control_failures:
            return f"방제 실패 {s.control_failures}회", "critical"
        return "격리·방제 중", "critical"
    if s.plant_state.ready:
        return "수확 가능", "ready"
    return "정상", "positive"


def is_warning(line):
    """경고로 볼 로그인지. '방제 완료, 격리 해제'처럼 좋은 소식은 경고가 아니다."""
    return any(k in line for k in WARN_WORDS) and not any(k in line for k in GOOD_WORDS)


def _r(v, n=2):
    return round(v, n)


class Simulation:
    def __init__(self):
        self.running = True
        self.speed_ms = DEFAULT_SPEED
        self.auto_replant = True
        self.overrides = {}                     # 관리자가 고친 작물 적정 조건 {작물: {키: 값}} — 초기화해도 남는다
        self.logs = deque(maxlen=LOG_MAX)       # {seq, zone, text, warn}
        self._harvest_ids = itertools.count(1)
        self._seq = itertools.count(1)
        self.epoch = 0                          # 초기화할 때마다 바뀐다 (웹은 전부 다시 받는다)
        self._changed = asyncio.Event()
        self.reset()

    # ---------- 진행 ----------
    def reset(self):
        self.farm = make_farm()
        self.farm.auto_replant = self.auto_replant
        for name in self.overrides:
            self._apply_profile(name)
        self.weather_delta = 0
        self.tick = 0
        self.epoch += 1
        self.history = [deque(maxlen=HISTORY) for _ in self.farm.sections]
        self.nights = deque(maxlen=HISTORY)
        self.ledger = deque(maxlen=LEDGER_DAYS)   # 끝난 날의 {day, revenue, cost, profit}
        self.harvest_events = deque(maxlen=10)    # 최근 수확 (화면의 수확 연출용, 금액 포함)
        self._ledger_day, self._day_start = self.farm.day, (0, 0, 0)
        self.logs.clear()
        self.record()
        self.notify()

    def step(self):
        self.run(lambda: self.farm.process(DT))
        self.tick += 1
        self.record()
        self._close_day()
        self.notify()

    async def run_forever(self):
        while True:
            if self.running:
                self.step()
            await asyncio.sleep(self.speed_ms / 1000)

    def record(self):
        for hist, s in zip(self.history, self.farm.sections):
            hist.append([_r(get(s.env_state)) for *_, get, _ in METRICS])
        self.nights.append(not (6 <= self.farm.hour < 18))

    def _close_day(self):
        """날이 바뀌면 지난 하루의 매출·비용·순이익(끝난 재배 기준)을 정산 기록에 남긴다."""
        if self.farm.day == self._ledger_day:
            return
        self.ledger.append(self._today())
        self._day_start = totals(self.farm.cycles)
        self._ledger_day = self.farm.day

    def _today(self):
        cost, rev, profit = (now - start for now, start in zip(totals(self.farm.cycles), self._day_start))
        return dict(day=self._ledger_day, revenue=round(rev), cost=round(cost), profit=round(profit))

    # ---------- 변경 알림 ----------
    @property
    def changed(self) -> asyncio.Event:
        """다음 변경 때 set되는 이벤트. 기다리기 전에 먼저 받아 두어야 놓치지 않는다."""
        return self._changed

    def notify(self):
        self._changed.set()
        self._changed = asyncio.Event()

    # ---------- 로그 ----------
    def stamp(self):
        h = self.farm.hour
        return f"Day{self.farm.day} {int(h):02d}:{int(h % 1 * 60):02d}"

    def run(self, action):
        """모델 함수를 실행하고, 그동안 print로 찍힌 로그와 새로 생긴 수확을 모은다."""
        before = len(self.farm.harvests)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            result = action()
        for line in buf.getvalue().splitlines():
            self.write(f"{self.stamp()}  {line}", is_warning(line))
        self._record_harvests(before)
        return result

    def _record_harvests(self, before):
        """새 수확마다 그 재배의 매출·비용·순이익을 계산해 둔다 (자동 수확·직접 수확 모두)."""
        for _day, zone, crop, kg, quality, price in self.farm.harvests[before:]:
            section = next(s for s in self.farm.sections if s.name == zone)
            cycle = next(c for c in reversed(section.cycles) if c["outcome"] == "수확")
            cost, rev, profit = cycle_result(cycle)
            self.harvest_events.append(dict(
                id=next(self._harvest_ids), zone=zone, crop=crop, kg=_r(kg, 1), quality=_r(quality, 1),
                price=round(price), revenue=round(rev), cost=round(cost), profit=round(profit)))

    def write(self, text, warn=False):
        m = re.search(r"구역\d+", text)
        self.logs.append(dict(seq=next(self._seq), zone=m.group() if m else None, text=text, warn=warn))

    # ---------- 사람의 조작 ----------
    def section(self, index):
        return self.farm.sections[index]

    def plant(self, index, crop):
        ok = self.run(lambda: self.section(index).plant(self.profile(crop)))
        self.notify()
        return ok

    def harvest(self, index):
        result = self.run(lambda: self.farm.harvest(self.section(index)))
        self.notify()
        return result is not None

    def plow(self, index):
        ok = self.run(self.section(index).plow)
        self.notify()
        return ok

    def harvest_all(self):
        ready = [s for s in self.farm.sections if s.plant_state and s.plant_state.ready]
        if not ready:
            self.write("※ 수확할 수 있는 구역이 없습니다.")
        for s in ready:
            self.run(lambda: self.farm.harvest(s))
        self.notify()
        return len(ready)

    def inject_pests(self, index):
        s = self.section(index)
        if not (s.plant_state and s.plant_state.alive):
            self.write(f"※ {s.label}에는 살아 있는 작물이 없습니다.")
            self.notify()
            return False
        s.plant_state.pests = True
        self.write(f"※ 시뮬레이터: {s.label}에 병충해 발생", True)
        self.notify()
        return True

    def set_device_mode(self, index, key, mode):
        """장치 운전 방식: auto(자동) / on·off(수동). 없는 장치·방식이면 KeyError·ValueError"""
        s = self.section(index)
        device = s.devices.by_key[key]
        changed = self.run(lambda: device.set_mode(mode, s.log))
        self.notify()
        return changed

    def dose(self, index, key):
        """급수·비료를 지금 한 번 준다."""
        s = self.section(index)
        device = s.devices.by_key[key]
        if not hasattr(device, "dose_now"):
            raise ValueError(f"{device.label}는 한 번 주기를 할 수 없습니다.")
        if not (s.plant_state and s.plant_state.alive):
            self.write(f"※ {s.label}에는 살아 있는 작물이 없습니다.")
            self.notify()
            return False
        readings = s.sensors.read_all(s.env_state)
        self.run(lambda: device.dose_now(readings, s.env_state.plant_profile, s.log))
        self.notify()
        return True

    def set_weather(self, delta):
        self.weather_delta = delta
        self.farm.weather.base_temp = 12 + delta
        self.write(f"※ 시뮬레이터: 바깥 평균기온 {12 + delta:.0f}°C" + (" (평년)" if not delta else ""))
        self.notify()

    def set_season(self, season):
        self.farm.weather.jump_to(season, self.farm.hours / 24 + 1)
        self.write(f"※ 시뮬레이터: 계절을 {season}(으)로 옮겼습니다.")
        self.notify()

    def set_speed(self, ms):
        self.speed_ms = min(SPEED_RANGE[1], max(SPEED_RANGE[0], int(ms)))
        self.notify()

    def set_running(self, running):
        self.running = bool(running)
        self.notify()

    def set_auto_replant(self, on):
        self.auto_replant = self.farm.auto_replant = bool(on)
        self.notify()

    # ---------- 작물 적정 조건 ----------
    def profile(self, name):
        """새로 심을 작물 정보: 기본값에 관리자가 고친 값을 덮는다."""
        p = make_profile(name)
        for key, value in self.overrides.get(name, {}).items():
            setattr(p, PROFILE_FIELDS[key], value)
        return p

    def update_profile(self, name, values: dict):
        """작물 적정 조건을 고친다. 지금 자라는 같은 작물에도 바로 적용된다. 잘못된 값이면 ValueError"""
        clean = {}
        for key, value in values.items():
            if key not in PROFILE_FIELDS:
                raise ValueError(f"고칠 수 없는 항목입니다: {key}")
            lo_limit, hi_limit = METRIC_RANGE[key]
            if key == "luminosity":
                if not lo_limit <= value <= hi_limit:
                    raise ValueError(f"조도 기준은 {lo_limit}~{hi_limit} 사이여야 합니다.")
                clean[key] = float(value)
                continue
            lo, hi = value
            if not (lo_limit <= lo < hi <= hi_limit):
                raise ValueError(f"{key} 범위는 {lo_limit}~{hi_limit} 안에서 하한 < 상한이어야 합니다.")
            clean[key] = (float(lo), float(hi))
        self.overrides[name] = {**self.overrides.get(name, {}), **clean}
        self._apply_profile(name)
        self.write(f"※ 관리자: {name} 적정 조건을 바꿨습니다.")
        self.notify()

    def reset_profile(self, name):
        self.overrides.pop(name, None)
        self._apply_profile(name)
        self.write(f"※ 관리자: {name} 적정 조건을 기본값으로 되돌렸습니다.")
        self.notify()

    def _apply_profile(self, name):
        """자동 재파종용 작물 정보와, 그 작물이 자라는 구역들의 작물 정보를 지금 설정으로 맞춘다."""
        want = self.profile(name)
        targets = [self.farm.profiles.get(name)] + [
            s.env_state.plant_profile for s in self.farm.sections if s.env_state.plant_profile.species == name]
        for p in filter(None, targets):
            for attr in PROFILE_FIELDS.values():
                setattr(p, attr, getattr(want, attr))

    # ---------- 웹으로 보낼 값 ----------
    @staticmethod
    def meta():
        return dict(
            crops=CROPS,
            zones=ZONES,
            metrics=[dict(key=k, title=t, range=rng, unit=u) for k, t, rng, u, *_ in METRICS],
            weather=[dict(label=label, delta=d) for label, d in WEATHER],
            seasons=[name for name, _ in SEASONS],
            yearDays=YEAR_DAYS,
            devices=[dict(key=d.key, label=d.label, modes=list(d.modes)) for d in Devices()],
            speedRange=SPEED_RANGE,
            history=HISTORY,
            stepsPerDay=STEPS_PER_DAY,
        )

    def snapshot(self):
        f, w = self.farm, self.farm.weather
        cost, rev, profit = totals(f.cycles)
        return dict(
            running=self.running, speed=self.speed_ms, weatherDelta=self.weather_delta,
            autoReplant=self.auto_replant,
            day=f.day, hour=_r(f.hour, 4), hours=_r(f.hours, 4),
            weather=dict(temperature=_r(w.temperature, 1), humidity=_r(w.humidity, 1),
                         sunlight=round(w.sunlight), cloud=_r(w.cloud), season=w.season,
                         seasonDay=int(w.phase * YEAR_DAYS + YEAR_DAYS / 8) % (YEAR_DAYS // 4) + 1,
                         sky="밤" if w.sunlight <= 0 else ("흐림" if w.cloud > 0.5 else "맑음")),
            sections=[self._section(i, s) for i, s in enumerate(f.sections)],
            harvests=[dict(day=d, zone=z, crop=c, kg=_r(kg, 1), quality=_r(q, 1), price=round(p))
                      for d, z, c, kg, q, p in f.harvests[-10:]][::-1],
            harvestCount=len(f.harvests), harvestKg=_r(sum(h[3] for h in f.harvests), 1),
            harvestEvents=list(self.harvest_events),
            totals=dict(cost=round(cost), revenue=round(rev), profit=round(profit)),
            ledger=[*self.ledger, self._today()],
            prices=self._prices(),
            crops=self._crops(),
        )

    def _section(self, i, s):
        ps, e, p, d = s.plant_state, s.env_state, s.env_state.plant_profile, s.devices
        label, tone = section_status(s)
        price = self.farm.market.price(p.species)
        items, cost, expected = section_money(s, price)
        plant = None
        if ps:
            left = ps.hours_to_harvest()
            plant = dict(alive=ps.alive, pests=ps.pests, ready=ps.ready, health=_r(ps.health, 1),
                         growth=_r(ps.growth, 1), stage=p.stage(ps.growth), ageDays=_r(ps.age_hours / 24),
                         avgHealth=_r(ps.avg_health, 1), daysToHarvest=None if left is None else _r(left / 24),
                         expectedKg=_r(p.yield_kg * ps.avg_health / 100, 1))
        return dict(
            index=i, name=s.name, label=s.label, species=p.species, status=dict(label=label, tone=tone),
            closed=s.is_closed, controlFailures=s.control_failures, plant=plant,
            stages=[[name, start] for name, start in p.stages], growDays=p.grow_days,
            env=[_r(get(e)) for *_, get, _ in METRICS],
            bands=[list(band(p)) for *_, band in METRICS],
            devices=dict(heater=d.heater, cooler=d.cooler, fan=d.fan, humidifier=d.humidifier,
                         dehumidifier=d.dehumidifier, light=d.light, water=d.water_l > 0,
                         fertilizer=d.fertilizer_g > 0, totalWater=_r(d.total_water_l, 1),
                         totalFertilizer=_r(d.total_fertilizer_g, 1), totalKwh=_r(d.total_energy_kwh),
                         powerKw=_r(d.power_kw()),
                         modes={x.key: x.mode for x in d}, reasons={x.key: x.reason for x in d}),
            money=dict(items=[[n, round(v)] for n, v in items], cost=round(cost),
                       expected=None if expected is None else round(expected), price=round(price)),
        )

    def _prices(self):
        m = self.farm.market
        out = {}
        for name in m.base:
            hist = m.history[name]
            now = m.price(name)
            day_ago = hist[-STEPS_PER_DAY] if len(hist) > STEPS_PER_DAY else hist[0]
            out[name] = dict(now=round(now), base=m.base[name], change=_r((now / day_ago - 1) * 100))
        return out

    def _crops(self):
        """작물별 적정 조건(지금 설정), 기본값에서 바뀌었는지, 지금 시세로 심었을 때 하루당 예상 순이익"""
        f = self.farm
        out = {}
        for name in CROPS:
            p = f.profiles[name]
            daily = economics.daily_profit(name, p.yield_kg, p.grow_days, f.market.price(name), f.cycles)
            out[name] = dict(
                changed=name in self.overrides, dailyProfit=round(daily), growDays=p.grow_days,
                **{key: (getattr(p, attr) if key == "luminosity" else list(getattr(p, attr)))
                   for key, attr in PROFILE_FIELDS.items()})
        return out

    def sync(self, cursor):
        """cursor(웹이 마지막으로 받은 epoch·tick·로그 번호) 이후에 바뀐 것만 담은 메시지와 새 cursor.
        처음이거나 초기화됐거나 너무 많이 밀렸으면 전부 보낸다."""
        gap = self.tick - cursor.get("tick", 0)
        full = cursor.get("epoch") != self.epoch or gap > HISTORY or gap < 0
        n = None if full else gap
        tail = lambda seq: list(seq)[-n:] if n else ([] if n == 0 else list(seq))
        last_seq = 0 if full else cursor.get("seq", 0)
        msg = dict(
            full=full, epoch=self.epoch, tick=self.tick,
            state=self.snapshot(),
            history=[tail(h) for h in self.history],
            nights=tail(self.nights),
            priceHistory={name: [round(v) for v in tail(h)] for name, h in self.farm.market.history.items()},
            logs=[e for e in self.logs if e["seq"] > last_seq],
        )
        new_seq = self.logs[-1]["seq"] if self.logs else last_seq
        return msg, dict(epoch=self.epoch, tick=self.tick, seq=new_seq)
