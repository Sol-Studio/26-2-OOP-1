import random
import unittest

import math

from core import economics
from core.market import Market
from types import SimpleNamespace

from core.plant import PlantProfile, PlantState
from core.environment import EnvState
from core.section import FarmSection
from core.farm import Farm
from core.weather import Weather
from core.devices import Device, OnOffDevice, Heater, Cooler, Fan, GrowLight, Irrigation, Fertilizer
from core.sensors import Sensor, SensorPanel, Readings, TemperatureSensor

DT = 1 / 6


def profile():
    return PlantProfile("테스트", (15, 22), 15000, (55, 75), humidity_range=(60, 80),
                        nutrient_range=(1.0, 1.6), grow_days=6, yield_kg=4.0)


def ideal_env(p=None):
    return EnvState(p or profile(), 18, 70, 600, 65, 30000, 1.3)


def ctx(closed=False, hour=12.0, outside=20.0):
    logs = []
    return SimpleNamespace(closed=closed, hour=hour, outside=outside, log=logs.append), logs


def readings(**kw):
    base = dict(temperature=18, humidity=70, co2=600, soil_humidity=65, nutrient=1.3, luminosity=30000)
    base.update(kw)
    return Readings(**base)


class OverripeTest(unittest.TestCase):
    def test_health_drops_even_in_ideal_environment(self):
        random.seed(0)
        plant = PlantState(growth=100.0)
        env = ideal_env()
        for _ in range(60):          # 10시간
            plant.update(env, DT)
        self.assertLess(plant.health, 95)
        self.assertAlmostEqual(plant.overripe_hours, 10, places=6)

    def test_overripe_eventually_dies(self):
        random.seed(0)
        plant = PlantState(growth=100.0)
        env = ideal_env()
        for _ in range(700):
            plant.update(env, DT)
        self.assertFalse(plant.alive)

    def test_growing_plant_is_not_affected(self):
        random.seed(0)
        plant = PlantState(growth=10.0)
        env = ideal_env()
        plant.update(env, DT)
        self.assertEqual(plant.overripe_hours, 0)
        self.assertEqual(plant.health, 100)


class AutoHarvestTest(unittest.TestCase):
    def make(self, auto):
        s = FarmSection(ideal_env(), PlantState(growth=100.0), False, name="구역1")
        return s, Farm([s], weather=Weather(), auto_harvest=auto)

    def test_auto_harvest_collects_and_empties_section(self):
        s, farm = self.make(True)
        farm.process()
        self.assertIsNone(s.plant_state)
        self.assertEqual(len(farm.harvests), 1)

    def test_manual_mode_leaves_plant(self):
        s, farm = self.make(False)
        farm.process()
        self.assertIsNotNone(s.plant_state)
        self.assertEqual(farm.harvests, [])


class SensorTest(unittest.TestCase):
    def test_panel_reads_all_values(self):
        env = ideal_env()
        r = SensorPanel().read_all(env)
        self.assertEqual((r.temperature, r.humidity, r.co2, r.soil_humidity, r.nutrient),
                         (18, 70, 600, 65, 1.3))

    def test_noise_changes_reading_and_custom_sensor_works(self):
        random.seed(1)
        self.assertNotEqual(TemperatureSensor(noise=1.0).read(ideal_env()), 18)

        class Const(Sensor):
            key = "answer"

            def measure(self, env):
                return 42
        self.assertEqual(SensorPanel([Const()]).read_all(ideal_env()).answer, 42)


class DeviceTest(unittest.TestCase):
    def test_heater_hysteresis(self):
        h, (c, logs), p = Heater(), ctx(), profile()
        h.control(readings(temperature=14), p, c)
        self.assertTrue(h.on)
        h.control(readings(temperature=15.5), p, c)    # 15~16 사이: 유지
        self.assertTrue(h.on)
        h.control(readings(temperature=16.5), p, c)
        self.assertFalse(h.on)
        self.assertEqual(len(logs), 2)                  # 상태가 바뀔 때만 로그

    def test_cooler_and_fan_rules(self):
        p = profile()
        c, _ = ctx()
        cooler = Cooler()
        cooler.control(readings(temperature=23), p, c)
        self.assertTrue(cooler.on)
        fan = Fan()
        fan.control(readings(temperature=20, co2=1300), p, c)
        self.assertTrue(fan.on)
        closed, _ = ctx(closed=True)
        fan.control(readings(temperature=20, co2=1300), p, closed)
        self.assertFalse(fan.on)                        # 격리 중엔 닫는다

    def test_fan_does_not_let_in_cold_air_for_low_co2(self):
        p = profile()                                   # 적정 온도 하한 15°C
        warm, _ = ctx(outside=12)                       # 하한보다 3°C 낮은 정도는 괜찮다
        fan = Fan()
        fan.control(readings(temperature=18, co2=250), p, warm)
        self.assertTrue(fan.on)                         # 바깥이 따뜻하면 CO2 보충 환기
        cold, logs = ctx(outside=0)
        fan.control(readings(temperature=18, co2=250), p, cold)
        self.assertFalse(fan.on)                        # 바깥이 추우면 보온이 우선
        fan.control(readings(temperature=18, co2=1300), p, cold)
        self.assertTrue(fan.on)                         # CO2 과다는 추워도 환기

    def test_fan_vents_heat_only_when_outside_is_cooler(self):
        p = profile()                                   # 적정 온도 상한 22°C
        fan = Fan()
        hot, logs = ctx(outside=31)
        fan.control(readings(temperature=25, co2=600), p, hot)
        self.assertFalse(fan.on)                        # 바깥이 더 더우면 열어 봐야 더워진다
        mild, _ = ctx(outside=16)
        fan.control(readings(temperature=25, co2=600), p, mild)
        self.assertTrue(fan.on)                         # 바깥이 시원하면 환기로 식힌다
        fan.control(readings(temperature=25, co2=600), p, hot)
        self.assertFalse(fan.on)                        # 열려 있다가 바깥이 더워지면 닫는다
        fan.control(readings(temperature=18, co2=250), p, hot)
        self.assertFalse(fan.on)                        # 바깥이 너무 더우면 CO2 부족으로도 안 연다

    def test_light_only_between_6_and_22(self):
        p, light = profile(), GrowLight()
        day, _ = ctx(hour=10)
        light.control(readings(luminosity=5000), p, day)
        self.assertGreater(light.level, 0)
        night, _ = ctx(hour=23)
        light.control(readings(luminosity=5000 + light.level * GrowLight.LUX), p, night)
        self.assertEqual(light.level, 0)

    def test_dosing_targets_midpoint_and_accumulates(self):
        p, c = profile(), ctx()[0]
        water, fert = Irrigation(), Fertilizer()
        water.control(readings(soil_humidity=45), p, c)
        self.assertAlmostEqual(water.amount, (65 - 45) / 2.0)
        fert.control(readings(nutrient=0.5), p, c)
        self.assertAlmostEqual(fert.amount, (1.3 - 0.5) / 0.02)
        water.end_step()
        self.assertEqual(water.amount, 0)
        self.assertGreater(water.total, 0)

    def test_new_device_plugs_into_section_without_changing_process(self):
        class Buzzer(OnOffDevice):
            key, label, power_kw = "buzzer", "경보기", 0.1

            def decide(self, r, p, ctx):
                return r.temperature > 30, "고온"

        s = FarmSection(ideal_env(), PlantState(), False)
        s.devices.items.append(Buzzer())
        s.devices.by_key["buzzer"] = s.devices.items[-1]
        s.env_state.temperature = 35
        random.seed(0)
        s.process(Weather(), 12.0, DT)
        self.assertTrue(s.devices.by_key["buzzer"].on)
        self.assertIsInstance(s.devices.by_key["buzzer"], Device)


class SectionTest(unittest.TestCase):
    def test_dead_plant_shuts_devices_off_but_keeps_totals(self):
        s = FarmSection(ideal_env(), PlantState(health=0.01), False)
        s.devices.by_key["heater"].on = True
        s.devices.by_key["irrigation"].total = 7
        s.env_state.temperature = 40
        random.seed(0)
        s.process(Weather(), 12.0, 1.0)
        self.assertFalse(s.plant_state.alive)
        self.assertFalse(s.devices.heater)
        self.assertEqual(s.devices.total_water_l, 7)

    def test_pest_isolates_section_and_closes_fan(self):
        s = FarmSection(ideal_env(), PlantState(pests=True), False)
        s.devices.by_key["fan"].on = True
        random.seed(0)
        s.process(Weather(), 12.0, DT)
        self.assertTrue(s.is_closed)
        self.assertFalse(s.devices.fan)


class EconomicsTest(unittest.TestCase):
    def grown(self, quality=100.0):
        s = FarmSection(ideal_env(), None, False)
        s.plant(profile())
        s.plant_state.growth = 100.0
        s.plant_state.age_hours = 10
        s.plant_state.health_hours = 10 * quality
        return s

    def test_cycle_cost_counts_only_usage_since_planting(self):
        s = FarmSection(ideal_env(), None, False)
        s.devices.by_key["irrigation"].total = 100        # 이전 재배에서 쓴 물
        s.plant(profile())
        s.devices.by_key["irrigation"].total = 130
        self.assertAlmostEqual(s.cycle_usage()[1], 30)

    def test_second_crop_does_not_inherit_first_cost(self):
        s = self.grown()
        s.devices.by_key["fertilizer"].total = 50
        s.harvest()
        self.assertAlmostEqual(s.cycles[0]["fertilizer_g"], 50)
        s.plant(profile())
        self.assertEqual(s.cycle_usage(), (0, 0, 0))

    def test_harvest_revenue_depends_on_quality(self):
        high, low = self.grown(95), self.grown(50)
        high.harvest(), low.harvest()
        r_high, r_low = (economics.cycle_result(s.cycles[0])[1] / s.cycles[0]["kg"] for s in (high, low))
        self.assertGreater(r_high, r_low)

    def test_plow_and_dead_plant_are_losses(self):
        plowed = self.grown()
        plowed.plow()
        dead = self.grown()
        dead.plant_state.alive = False
        dead.harvest()
        for s in (plowed, dead):
            cost, rev, profit = economics.cycle_result(s.cycles[0])
            self.assertEqual(rev, 0)
            self.assertLess(profit, 0)

    def test_farm_totals_sum_all_sections(self):
        a, b = self.grown(), self.grown()
        a.harvest(), b.plow()
        farm = Farm([a, b])
        cost, rev, profit = economics.totals(farm.cycles)
        self.assertAlmostEqual(profit, rev - cost)
        self.assertEqual(len(farm.cycles), 2)



class MarketTest(unittest.TestCase):
    def test_price_stays_within_range_and_moves(self):
        random.seed(1)
        m = Market({"상추": 8000})
        seen = set()
        for _ in range(6 * 24 * 60):
            m.step(DT)
            seen.add(round(m.price("상추")))
            self.assertGreaterEqual(m.price("상추"), 8000 * 0.5 - 1)
            self.assertLessEqual(m.price("상추"), 8000 * 1.8 + 1)
        self.assertGreater(len(seen), 100)

    def test_selling_lowers_price_then_it_recovers(self):
        random.seed(2)
        m = Market({"상추": 8000})
        m.sell("상추", 400)
        low = m.price("상추")
        self.assertLess(low, 8000 * 0.95)
        from core import market
        old, market.VOLATILITY = market.VOLATILITY, 0.0
        try:
            for _ in range(6 * 24 * 10):
                m.step(DT)
        finally:
            market.VOLATILITY = old
        self.assertGreater(m.price("상추"), low)
        self.assertLess(m.price("상추"), 8000)

    def test_history_is_recorded_each_step(self):
        m = Market({"상추": 8000})
        for _ in range(5):
            m.step(DT)
        self.assertEqual(len(m.history["상추"]), 6)


class AutoReplantTest(unittest.TestCase):
    def setUp(self):
        self.profiles = {"상추": PlantProfile("상추", (15, 22), 15000, (55, 75), humidity_range=(60, 80),
                                               nutrient_range=(1.0, 1.6), grow_days=6, yield_kg=120),
                         "토마토": PlantProfile("토마토", (18, 27), 30000, (60, 80), humidity_range=(60, 80),
                                                nutrient_range=(2.0, 3.5), grow_days=12, yield_kg=360)}

    def farm(self, replant=True):
        s = FarmSection(ideal_env(self.profiles["상추"]), None, False, name="구역1")
        s.plant(self.profiles["상추"])
        s.plant_state.growth = 100.0
        s.plant_state.age_hours = 10
        s.plant_state.health_hours = 1000
        f = Farm([s], profiles=self.profiles)
        f.auto_replant = replant
        return f, s

    def test_replants_crop_with_best_daily_profit(self):
        f, s = self.farm()
        f.market.x["토마토"] = math.log(1.8)        # 토마토 시세 급등
        f.market.x["상추"] = math.log(0.5)
        f.harvest(s)
        self.assertEqual(s.env_state.plant_profile.species, "토마토")
        self.assertIsNotNone(s.plant_state)

    def test_follows_price_changes(self):
        f, s = self.farm()
        f.market.x["토마토"] = math.log(0.5)        # 토마토 폭락
        f.market.x["상추"] = math.log(1.8)
        f.harvest(s)
        self.assertEqual(s.env_state.plant_profile.species, "상추")

    def test_off_leaves_section_empty(self):
        f, s = self.farm(replant=False)
        f.harvest(s)
        self.assertIsNone(s.plant_state)

    def test_harvest_uses_market_price_and_lowers_it(self):
        f, s = self.farm(replant=False)
        f.market.x["상추"] = math.log(1.5)
        price = f.market.price("상추")
        f.harvest(s)
        self.assertAlmostEqual(f.harvests[0][5], price)
        self.assertAlmostEqual(economics.cycle_result(s.cycles[0])[1],
                               economics.revenue("상추", s.cycles[0]["kg"], s.cycles[0]["quality"], price))
        self.assertLess(f.market.price("상추"), price)

    def test_plow_does_not_replant(self):
        f, s = self.farm()
        s.plow()
        self.assertIsNone(s.plant_state)



class ColdSnapTest(unittest.TestCase):
    def test_every_crop_survives_three_days_of_cold_snap(self):
        """시뮬레이터의 한파(바깥 평균 2°C, 최저 약 -5°C)에서도 난방으로 버텨야 한다."""
        import contextlib, io
        from core.catalog import make_farm
        random.seed(7)
        farm = make_farm()
        farm.auto_harvest = False
        farm.weather.base_temp = 12 - 10
        with contextlib.redirect_stdout(io.StringIO()):
            for _ in range(6 * 72):
                farm.process(DT)
        dead = [s.label for s in farm.sections if not s.plant_state.alive]
        self.assertEqual(dead, [])
        for s in farm.sections:
            self.assertGreater(s.plant_state.health, 50, s.label)


class HeatWaveTest(unittest.TestCase):
    def test_every_crop_survives_three_days_of_heat_wave(self):
        """시뮬레이터의 폭염(바깥 평균 24°C, 최고 약 31°C)에서도 냉방으로 버텨야 한다."""
        import contextlib, io
        from core.catalog import make_farm
        random.seed(7)
        farm = make_farm()
        farm.auto_harvest = False
        farm.weather.base_temp = 12 + 12
        with contextlib.redirect_stdout(io.StringIO()):
            for _ in range(6 * 72):
                farm.process(DT)
        dead = [s.label for s in farm.sections if not s.plant_state.alive]
        self.assertEqual(dead, [])
        for s in farm.sections:
            self.assertGreater(s.plant_state.health, 50, s.label)


class AccountsTest(unittest.TestCase):
    def test_default_account_logs_in(self):
        from core.auth import Accounts
        self.assertTrue(Accounts().login("farmer", "evergrow"))

    def test_wrong_password_or_unknown_user_fails(self):
        from core.auth import Accounts
        a = Accounts()
        self.assertFalse(a.login("farmer", "wrong"))
        self.assertFalse(a.login("nobody", "evergrow"))
        self.assertEqual(a.failures, 2)

    def test_password_is_not_stored_as_plain_text(self):
        from core.auth import Accounts
        a = Accounts({})
        a.add("kim", "secret")
        self.assertNotIn("secret", a.users["kim"])
        self.assertTrue(a.login("kim", "secret"))

    def test_locks_after_max_failures_and_success_resets_count(self):
        from core.auth import Accounts
        a = Accounts()
        a.login("farmer", "x")
        a.login("farmer", "evergrow")
        self.assertEqual(a.failures, 0)
        for _ in range(Accounts.MAX_FAILURES):
            a.login("farmer", "x")
        self.assertTrue(a.locked)
        self.assertFalse(a.login("farmer", "evergrow"))



class ManualModeTest(unittest.TestCase):
    def test_manual_on_off_overrides_auto_and_auto_comes_back(self):
        p, (c, logs) = profile(), ctx()
        heater = Heater()
        self.assertTrue(heater.set_mode("on", logs.append))
        self.assertTrue(heater.on)                      # 바로 켜진다
        heater.control(readings(temperature=30), p, c)
        self.assertTrue(heater.on)                      # 더워도 수동이면 그대로
        self.assertFalse(heater.set_mode("on", logs.append))   # 같은 방식이면 바뀐 것 없음
        heater.set_mode("auto", logs.append)
        heater.control(readings(temperature=30), p, c)
        self.assertFalse(heater.on)                     # 자동으로 돌아오면 스스로 끈다
        self.assertTrue(any("수동 켜기" in m for m in logs))

    def test_light_manual_and_reason(self):
        p, (c, _) = profile(), ctx(hour=23)
        light = GrowLight()
        light.set_mode("on", print)
        light.control(readings(luminosity=0), p, c)
        self.assertEqual(light.level, 1.0)              # 밤이어도 수동이면 켠다
        light.set_mode("auto", print)
        light.control(readings(luminosity=0), p, c)
        self.assertEqual(light.level, 0)
        self.assertIn("밤", light.reason)

    def test_dosing_off_blocks_auto_and_dose_now_still_works(self):
        p, (c, logs) = profile(), ctx()
        water = Irrigation()
        with self.assertRaises(ValueError):
            water.set_mode("on", logs.append)           # 급수는 켜 둘 수 없다
        water.set_mode("off", logs.append)
        water.control(readings(soil_humidity=10), p, c)
        self.assertEqual(water.amount, 0)               # 자동 급수 멈춤
        water.dose_now(readings(soil_humidity=10), p, logs.append)
        self.assertAlmostEqual(water.amount, (65 - 10) / 2.0)
        self.assertIn("수동 급수", water.reason)


class SeasonTest(unittest.TestCase):
    def test_seasons_shift_temperature_and_day_length(self):
        from core.weather import YEAR_DAYS
        summer, winter = Weather(seasons=True), Weather(seasons=True)
        summer.jump_to("여름", 1)
        winter.jump_to("겨울", 1)
        summer.cloud = winter.cloud = 0
        random.seed(0)
        summer.update(15, DT, day=1.6)
        winter.update(15, DT, day=1.6)
        self.assertEqual((summer.season, winter.season), ("여름", "겨울"))
        self.assertAlmostEqual(summer.temperature - winter.temperature, 20, delta=1)
        summer.update(19, DT, day=1.8)                  # 여름엔 해가 길다 (일몰 20시)
        winter.update(17, DT, day=1.7)                  # 겨울엔 해가 짧다 (일몰 16시)
        self.assertGreater(summer.sunlight, 0)
        self.assertEqual(winter.sunlight, 0)
        w = Weather(seasons=True)
        w.update(12, DT, day=1 + YEAR_DAYS / 4)         # 30일 지나면 봄 → 여름
        self.assertEqual(w.season, "여름")

    def test_seasons_off_keeps_old_daily_cycle(self):
        w = Weather()
        w.update(12, DT, day=50)
        self.assertIsNone(w.season)
        self.assertAlmostEqual(w.temperature, 12 + 7 * math.sin(2 * math.pi * 3 / 24))


if __name__ == "__main__":
    unittest.main()
