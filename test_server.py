"""웹 서버(server/) 테스트. 실행: python -m unittest test_server -v
시뮬레이션 자동 진행(lifespan)은 켜지 않고, 필요한 만큼 직접 진행시킨다."""
import unittest

from fastapi.testclient import TestClient

from server import main
from server.simulation import HISTORY, Simulation


class ServerTest(unittest.TestCase):
    def setUp(self):
        main.sim = Simulation()
        main.accounts = main.Accounts()
        main.sessions.clear()
        self.client = TestClient(main.app)

    def login(self):
        r = self.client.post("/api/login", json=dict(user="farmer", password="evergrow"))
        self.assertEqual(r.status_code, 200)
        return {"Authorization": f"Bearer {r.json()['token']}"}

    def test_login_rules(self):
        self.assertEqual(self.client.post("/api/login", json=dict(user=" ", password="x")).status_code, 400)
        r = self.client.post("/api/login", json=dict(user="farmer", password="wrong"))
        self.assertEqual(r.status_code, 401)
        self.assertIn("1/5", r.json()["detail"])
        for _ in range(3):
            self.client.post("/api/login", json=dict(user="farmer", password="wrong"))
        r = self.client.post("/api/login", json=dict(user="farmer", password="wrong"))
        self.assertEqual(r.status_code, 423)
        # 잠기면 맞는 비밀번호도 안 된다
        r = self.client.post("/api/login", json=dict(user="farmer", password="evergrow"))
        self.assertEqual(r.status_code, 423)

    def test_api_needs_login(self):
        self.assertEqual(self.client.get("/api/meta").status_code, 401)
        self.assertEqual(self.client.post("/api/harvest-all").status_code, 401)
        h = self.login()
        self.assertEqual(self.client.get("/api/meta", headers=h).json()["crops"][0], "상추")
        self.client.post("/api/logout", headers=h)
        self.assertEqual(self.client.get("/api/meta", headers=h).status_code, 401)

    def test_section_actions(self):
        h = self.login()
        sim = main.sim
        self.assertFalse(self.client.post("/api/sections/0/harvest", headers=h).json()["ok"])   # 아직 덜 자람
        self.assertTrue(self.client.post("/api/sections/0/plow", headers=h).json()["ok"])
        self.assertIsNone(sim.farm.sections[0].plant_state)
        r = self.client.post("/api/sections/0/plant", headers=h, json=dict(crop="딸기"))
        self.assertTrue(r.json()["ok"])
        self.assertEqual(sim.farm.sections[0].env_state.plant_profile.species, "딸기")
        self.assertEqual(self.client.post("/api/sections/0/plant", headers=h, json=dict(crop="수박")).status_code, 422)
        self.assertEqual(self.client.post("/api/sections/9/harvest", headers=h).status_code, 404)
        self.assertTrue(self.client.post("/api/sections/1/pests", headers=h).json()["ok"])
        self.assertTrue(sim.farm.sections[1].plant_state.pests)
        self.assertTrue(any("병충해 발생" in e["text"] and e["warn"] for e in sim.logs))

    def test_sim_settings(self):
        h = self.login()
        sim = main.sim
        self.client.patch("/api/sim", headers=h, json=dict(running=False, speed=5, weather=-10, autoReplant=False))
        self.assertFalse(sim.running)
        self.assertEqual(sim.speed_ms, 20)                  # 범위 안으로 맞춘다
        self.assertEqual(sim.farm.weather.base_temp, 2)
        self.assertFalse(sim.farm.auto_replant)
        self.assertEqual(self.client.patch("/api/sim", headers=h, json=dict(weather=7)).status_code, 422)
        self.client.post("/api/sim/step", headers=h)
        self.assertEqual(sim.tick, 1)
        self.client.post("/api/sim/reset", headers=h)
        self.assertEqual(sim.tick, 0)
        self.assertEqual(sim.weather_delta, 0)
        self.assertFalse(sim.farm.auto_replant)             # 설정은 초기화해도 남는다

    def test_sync_sends_only_changes(self):
        sim = main.sim
        msg, cursor = sim.sync({})
        self.assertTrue(msg["full"])
        self.assertEqual(len(msg["history"][0]), 1)
        sim.step()
        sim.step()
        msg, cursor = sim.sync(cursor)
        self.assertFalse(msg["full"])
        self.assertEqual(len(msg["history"][0]), 2)
        self.assertEqual(len(msg["nights"]), 2)
        self.assertEqual(len(msg["priceHistory"]["상추"]), 2)
        msg, cursor = sim.sync(cursor)
        self.assertEqual(msg["history"][0], [])
        self.assertEqual(msg["logs"], [])
        for _ in range(HISTORY + 1):                        # 너무 밀리면 전부 다시 보낸다
            sim.step()
        self.assertTrue(sim.sync(cursor)[0]["full"])
        sim.reset()
        self.assertTrue(sim.sync(cursor)[0]["full"])

    def test_device_manual_control(self):
        h = self.login()
        sim = main.sim
        url = "/api/sections/0/devices"
        r = self.client.post(f"{url}/heater", headers=h, json=dict(mode="on"))
        self.assertTrue(r.json()["changed"])
        self.assertTrue(sim.farm.sections[0].devices.heater)
        state = sim.snapshot()["sections"][0]["devices"]
        self.assertEqual(state["modes"]["heater"], "on")
        self.assertIn("관리자", state["reasons"]["heater"])
        self.assertEqual(self.client.post(f"{url}/irrigation", headers=h, json=dict(mode="on")).status_code, 422)
        self.assertEqual(self.client.post(f"{url}/teleporter", headers=h, json=dict(mode="on")).status_code, 404)
        self.assertEqual(self.client.post(f"{url}/heater/dose", headers=h).status_code, 422)
        before = sim.farm.sections[0].devices.total_water_l
        self.assertTrue(self.client.post(f"{url}/irrigation/dose", headers=h).json()["ok"])
        self.assertGreater(sim.farm.sections[0].devices.total_water_l, before)

    def test_crop_settings_apply_to_growing_and_new_plants(self):
        h = self.login()
        sim = main.sim
        r = self.client.put("/api/crops/상추", headers=h, json=dict(temperature=[10, 30], luminosity=9000))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(sim.farm.sections[0].env_state.plant_profile.temperature_range, (10, 30))  # 구역1이 상추
        self.assertEqual(sim.farm.profiles["상추"].min_luminosity, 9000)
        crops = sim.snapshot()["crops"]
        self.assertTrue(crops["상추"]["changed"])
        self.assertEqual(crops["상추"]["temperature"], [10, 30])
        self.assertIn("dailyProfit", crops["토마토"])
        self.client.post("/api/sections/1/plow", headers=h)
        self.client.post("/api/sections/1/plant", headers=h, json=dict(crop="상추"))
        self.assertEqual(sim.farm.sections[1].env_state.plant_profile.temperature_range, (10, 30))
        self.client.post("/api/sim/reset", headers=h)
        self.assertEqual(sim.farm.sections[0].env_state.plant_profile.temperature_range, (10, 30))  # 초기화해도 남음
        self.assertEqual(self.client.put("/api/crops/상추", headers=h, json=dict(temperature=[30, 10])).status_code, 422)
        self.assertEqual(self.client.put("/api/crops/수박", headers=h, json=dict(luminosity=1)).status_code, 404)
        self.client.delete("/api/crops/상추", headers=h)
        self.assertEqual(sim.farm.sections[0].env_state.plant_profile.temperature_range, (15, 22))
        self.assertFalse(sim.snapshot()["crops"]["상추"]["changed"])

    def test_season_and_daily_ledger(self):
        h = self.login()
        sim = main.sim
        self.assertEqual(sim.snapshot()["weather"]["season"], "봄")
        self.client.patch("/api/sim", headers=h, json=dict(season="겨울"))
        sim.step()
        self.assertEqual(sim.snapshot()["weather"]["season"], "겨울")
        self.assertEqual(self.client.patch("/api/sim", headers=h, json=dict(season="장마")).status_code, 422)
        self.assertEqual(len(sim.snapshot()["ledger"]), 1)  # 오늘(진행 중)만
        for _ in range(6 * 24):
            sim.step()
        ledger = sim.snapshot()["ledger"]
        self.assertEqual([d["day"] for d in ledger], [1, 2])

    def test_harvest_event_has_money(self):
        h = self.login()
        sim = main.sim
        sim.farm.sections[0].plant_state.growth = 100      # 다 자랐다고 치고 수확
        self.assertTrue(self.client.post("/api/sections/0/harvest", headers=h).json()["ok"])
        (event,) = sim.snapshot()["harvestEvents"]
        self.assertEqual((event["zone"], event["crop"]), ("구역1", "상추"))
        self.assertGreater(event["revenue"], 0)
        self.assertEqual(event["profit"], event["revenue"] - event["cost"])
        self.client.post("/api/sim/reset", headers=h)
        self.assertEqual(sim.snapshot()["harvestEvents"], [])

    def test_websocket(self):
        h = self.login()
        token = h["Authorization"].split()[1]
        with self.client.websocket_connect(f"/api/ws?token={token}") as ws:
            msg = ws.receive_json()
            self.assertTrue(msg["full"])
            self.assertEqual(len(msg["state"]["sections"]), 6)
            self.client.post("/api/sim/step", headers=h)
            msg = ws.receive_json()
            self.assertFalse(msg["full"])
            self.assertEqual(msg["tick"], 1)


if __name__ == "__main__":
    unittest.main()
