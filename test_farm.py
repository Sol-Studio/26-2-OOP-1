import random
import unittest
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


if __name__ == "__main__":
    unittest.main()
