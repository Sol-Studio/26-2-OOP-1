"""모든 화면이 같이 쓰는 글꼴, 색, 그래프 정의"""
HISTORY = 6 * 24        # 그래프에 남길 단계 수 (24시간)
FONT = "Malgun Gothic"

COLOR = {
    "bg": "#f3f5f1", "card": "#ffffff", "line": "#c9d3cb", "ink": "#1d2620", "muted": "#6b7a70",
    "healthy": "#2f7d4a", "closed": "#c0582a", "dead": "#7a7a7a", "band": "#e1eee4",
    "night": "#e6e9ef", "plot": "#1f6fb2", "on": "#2f7d4a", "off": "#d9dfda",
    "ready": "#b8860b", "empty": "#f7f8f6",
}

# 그래프: (제목, 값 꺼내는 함수, y축 범위, 적정 범위 함수, 단위)
CHARTS = [
    ("온도",      lambda s: s.env_state.temperature,   (0, 40),     lambda p: p.temperature_range, "°C"),
    ("습도",      lambda s: s.env_state.humidity,      (20, 100),   lambda p: p.humidity_range, "%"),
    ("토양 습도", lambda s: s.env_state.soil_humidity, (0, 100),    lambda p: p.soil_humidity_range, "%"),
    ("양액 EC",   lambda s: s.env_state.nutrient,      (0, 4),      lambda p: p.nutrient_range, "mS/cm"),
    ("조도",      lambda s: s.env_state.luminosity,    (0, 70000),  lambda p: (p.min_luminosity, 70000), "lux"),
    ("CO2",       lambda s: s.env_state.gas_density,   (150, 1300), lambda p: p.co2_range, "ppm"),
]
