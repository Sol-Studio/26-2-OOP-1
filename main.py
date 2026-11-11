"""화면 없이 모델만 확인하는 실행 파일. 상추 한 구역을 키우면서 상태를 글자로 계속 출력한다."""
import time

from core.environment import EnvState
from core.farm import Farm
from core.plant import PlantProfile, PlantState
from core.section import FarmSection

if __name__ == "__main__":
    lettuce = PlantProfile("상추", (15, 22), 15000, (55, 75), humidity_range=(60, 80), nutrient_range=(1.0, 1.6),
                           grow_days=6, yield_kg=4.0)
    section1 = FarmSection(EnvState(lettuce, 17, 47, 600, 30, 30000), PlantState(True, False), False)
    farm = Farm([section1])
    while True:
        time.sleep(0.1)
        farm.process()      # 한 번에 10분 진행
        if not (section1.plant_state.alive and not section1.plant_state.ready):
            farm.harvest(section1)      # 다 자랐거나 죽었으면 수확·정리하고 다시 심는다
            section1.plant(lettuce)
        e, plant = section1.env_state, section1.plant_state
        print(f"  Day{farm.day} {farm.hour:05.2f}h  {e.temperature:5.1f}°C  {e.humidity:4.0f}%  "
              f"토양 {e.soil_humidity:4.0f}%  EC {e.nutrient:.2f}  {e.luminosity:7,.0f}lux  "
              f"건강 {plant.health:5.1f}  {lettuce.stage(plant.growth)} {plant.growth:3.0f}%")
