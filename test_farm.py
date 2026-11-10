import random
import unittest

import math

import economics
from market import Market
from types import SimpleNamespace

from main import (PlantProfile, EnvState, PlantState, FarmSection, Farm, Weather, Device, OnOffDevice,
                  Heater, Cooler, Fan, GrowLight, Irrigation, Fertilizer, Sensor, SensorPanel, Readings,
                  TemperatureSensor)

DT = 1 / 6


def profile():
    return PlantProfile("테스트", (15, 22), 15000, (55, 75), humidity_range=(60, 80),
                        nutrient_range=(1.0, 1.6), grow_days=6, yield_kg=4.0)


def ideal_env(p=None):
    return EnvState(p or profile(), 18, 70, 600, 65, 30000, 1.3)


def ctx(closed=False, hour=12.0):
    logs = []
    return SimpleNamespace(closed=closed, hour=hour, log=logs.append), logs


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


class CctvTest(unittest.TestCase):
    def test_draws_every_section_state_without_error(self):
        import tkinter as tk
        from cctv import draw_cctv
        from common import make_farm
        try:
            root = tk.Tk()
        except tk.TclError:
            self.skipTest("화면을 쓸 수 없는 환경")
        self.addCleanup(root.destroy)
        farm = make_farm()
        c = tk.Canvas(root, width=300, height=200)
        s = farm.sections[1]
        cases = [lambda: None,
                 lambda: setattr(s.plant_state, "growth", 5.0),
                 lambda: (setattr(s.plant_state, "growth", 90.0), setattr(s.plant_state, "pests", True)),
                 lambda: setattr(s, "is_closed", True),
                 lambda: setattr(s.plant_state, "alive", False),
                 lambda: setattr(s, "plant_state", None)]
        for case in cases:
            case()
            for hour in (3.0, 12.0):
                farm.hours = hour
                for compact in (False, True):
                    draw_cctv(c, 0, 0, 300, 200, s, farm, 2, compact=compact)


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
        import market
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


class PriceWindowTest(unittest.TestCase):
    def test_draws_for_each_range(self):
        import tkinter as tk
        from common import make_farm
        from price_window import PriceWindow
        try:
            root = tk.Tk()
        except tk.TclError:
            self.skipTest("화면을 쓸 수 없는 환경")
        self.addCleanup(root.destroy)
        app = SimpleNamespace(root=root, farm=make_farm())
        w = PriceWindow(app)
        w.deiconify()
        for _ in range(200):
            app.farm.market.step(DT)
        for d in (1, 7, 30):
            w.days.set(d)
            w.refresh()


if __name__ == "__main__":
    unittest.main()
