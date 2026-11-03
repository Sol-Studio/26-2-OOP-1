import time, random

class PlantProfile:
    def __init__(self, species:str, temperature_range:tuple, min_luminosity: float,
                soil_humidity_range: tuple):
        self.species = species
        self.temperature_range = temperature_range
        self.min_luminosity = min_luminosity
        self.soil_humidity_range = soil_humidity_range

class EnvState:
    def __init__(self, plant_profile:PlantProfile, temperature: float, humidity: float, 
                gas_density: float, soil_humidity: float, luminosity: float):
        self.plant_profile = plant_profile
        self.temperature = temperature
        self.humidity = humidity
        self.gas_density = gas_density
        self.soil_humidity = soil_humidity
        self.luminosity = luminosity

class PlantState:
    def __init__(self, alive: bool, pests: bool):
        self.alive = alive
        self.pests = pests

class FarmSection:
    def __init__(self, env_state:EnvState, plant_state: PlantState, is_closed: bool):
        self.env_state = env_state
        self.plant_state = plant_state
        self.is_closed = is_closed
    
    def process(self):
        if not self.plant_state.alive:
            print("식물이 죽었습니다.")
            return
        if self.plant_state.pests:
            print("병충해 발생이 감지되어 구역을 격리합니다.")
            self.is_closed = True
        else:
            print("식물이 건강합니다.")
        pass

class Farm:
    def __init__(self, sections:list):
        self.sections = sections
    
    def process(self):
        for section in self.sections:
            section.process()


if __name__ == "__main__":
    section1 = FarmSection(EnvState(PlantProfile("상추", (0, 100), 20000, (0, 100)), 17, 47, 0.2, 30, 30000), PlantState(True, False), False)
    farm = Farm([section1])
    while True:
        time.sleep(0.1)
        farm.process()
        if random.random() < 0.1:
            section1.plant_state.pests = True
