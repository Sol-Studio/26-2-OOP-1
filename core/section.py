"""재배 구역 하나: 환경·식물·장치·센서를 묶어 한 단계씩 진행"""
import random
from types import SimpleNamespace

from core.devices import Devices
from core.environment import EnvState
from core.plant import PlantProfile, PlantState
from core.sensors import SensorPanel
from core.weather import Weather


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
