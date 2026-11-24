"""모든 화면이 같이 쓰는 글꼴, 색, 그래프 정의.
색과 글꼴은 당근마켓 SEED Design(Apache-2.0, github.com/daangn/seed-design)의 라이트 테마 토큰을 따른다."""
import os

HISTORY = 6 * 24        # 그래프에 남길 단계 수 (24시간)


def _pick_font():
    """SEED는 Windows에서 Pretendard를 쓴다. 설치돼 있지 않으면 맑은 고딕으로."""
    dirs = [os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Windows", "Fonts")]
    for d in dirs:
        names = [n.lower() for n in os.listdir(d)] if os.path.isdir(d) else []
        if any(n.startswith("pretendardvariable") for n in names):
            return "Pretendard Variable"
        if any(n.startswith("pretendard") for n in names):
            return "Pretendard"
    return "Malgun Gothic"


FONT = _pick_font()

# SEED 팔레트 중 쓰는 값 (palette-이름-단계)
SEED = {
    "carrot-100": "#fff2ec", "carrot-600": "#ff6600", "carrot-700": "#e14d00",
    "gray-00": "#ffffff", "gray-100": "#f7f8f9", "gray-200": "#f3f4f5", "gray-300": "#eeeff1",
    "gray-400": "#dcdee3", "gray-500": "#d1d3d8", "gray-700": "#868b94", "gray-800": "#555d6d",
    "gray-900": "#2a3038", "gray-1000": "#1a1c20",
    "green-200": "#d9f6e9", "green-700": "#079171", "red-100": "#fdf0f0", "red-500": "#fe928d",
    "red-700": "#fa342c", "yellow-300": "#fbdc65", "blue-700": "#217cf9", "purple-700": "#8969ea",
    "yellow-600": "#c49725",
}

# 화면에서 쓰는 이름 → SEED 시맨틱 토큰
COLOR = {
    "bg": SEED["gray-200"],          # bg.layer-basement  창 바탕
    "card": SEED["gray-00"],         # bg.layer-default   카드·패널
    "pressed": SEED["gray-100"],     # bg.layer-default-pressed
    "empty": SEED["gray-100"],       # bg.neutral-muted   빈 구역
    "line": SEED["gray-400"],        # stroke.neutral-weak (불투명 근사)
    "ink": SEED["gray-1000"],        # fg.neutral
    "muted": SEED["gray-800"],       # fg.neutral-muted
    "subtle": SEED["gray-700"],      # fg.neutral-subtle
    "brand": SEED["carrot-600"],     # bg.brand-solid / fg.brand
    "brand_pressed": SEED["carrot-700"],
    "brand_weak": SEED["carrot-100"],
    "healthy": SEED["green-700"],    # fg.positive        정상·이익
    "closed": SEED["red-700"],       # fg.critical        격리·범위 이탈·손실
    "closed_weak": SEED["red-100"],  # bg.critical-weak   격리 중 카드
    "ready": SEED["blue-700"],       # fg.informative     수확 가능
    "dead": SEED["gray-700"],
    "dead_bg": SEED["gray-300"],
    "band": SEED["green-200"],       # 그래프의 적정 범위 띠
    "night": SEED["gray-300"],
    "day": SEED["yellow-300"],
    "plot": SEED["carrot-600"],      # 그래프 선·생장 막대·선택 테두리 (브랜드 강조)
    "down": SEED["blue-700"],        # 시세 하락
    "on": SEED["carrot-600"],        # 켜진 장치
    "off": SEED["gray-300"],
    "on_text": SEED["gray-00"],      # fg.on-brand-solid
    "dark": SEED["gray-1000"],       # 로그창·모바일 상태 표시줄
    "dark_text": SEED["gray-400"],
    "dark_select": SEED["gray-800"],
    "dark_warn": "#ff9364",          # palette carrot-500, 어두운 바탕의 경고 줄
}


def health_color(health):
    """건강 막대 색: 상태가 아니라 건강도 자체로 정한다 (positive → warning → critical)."""
    return COLOR["healthy"] if health >= 70 else SEED["yellow-600"] if health >= 40 else COLOR["closed"]


def apply_style(root):
    """ttk 위젯(버튼·입력칸·선택 상자·탭 버튼)을 SEED 모양으로 맞춘다. 창을 만들 때 한 번 부른다."""
    from tkinter import ttk
    s = ttk.Style(root)
    s.theme_use("clam")
    s.configure(".", font=(FONT, 9), background=COLOR["bg"], foreground=COLOR["ink"],
                bordercolor=COLOR["line"], lightcolor=COLOR["card"], darkcolor=COLOR["card"],
                focuscolor=COLOR["brand"], troughcolor=COLOR["off"])
    s.configure("TButton", background=COLOR["card"], padding=(10, 4), borderwidth=1)
    s.map("TButton", background=[("pressed", COLOR["off"]), ("active", COLOR["pressed"])])
    s.configure("Brand.TButton", background=COLOR["brand"], foreground=COLOR["on_text"],
                bordercolor=COLOR["brand"], lightcolor=COLOR["brand"], darkcolor=COLOR["brand"],
                font=(FONT, 9, "bold"))
    s.map("Brand.TButton", background=[("pressed", COLOR["brand_pressed"]), ("active", COLOR["brand_pressed"])])
    # 칩 탭(로그 필터·시세 기간): 선택되면 어두운 바탕에 흰 글씨
    s.configure("Toolbutton", background=COLOR["card"], padding=(8, 2), borderwidth=1)
    s.map("Toolbutton", background=[("selected", COLOR["ink"]), ("active", COLOR["pressed"])],
          foreground=[("selected", COLOR["on_text"])])
    s.configure("TEntry", fieldbackground=COLOR["card"], padding=4)
    s.map("TEntry", bordercolor=[("focus", COLOR["brand"])], lightcolor=[("focus", COLOR["brand"])])
    s.configure("TCombobox", fieldbackground=COLOR["card"], background=COLOR["card"], arrowcolor=COLOR["muted"])
    s.map("TCombobox", fieldbackground=[("readonly", COLOR["card"])], bordercolor=[("focus", COLOR["brand"])])
    s.configure("TCheckbutton", background=COLOR["bg"], indicatorbackground=COLOR["card"])
    s.map("TCheckbutton", indicatorbackground=[("selected", COLOR["brand"])],
          indicatorforeground=[("selected", COLOR["on_text"])], background=[("active", COLOR["bg"])])


# 그래프: (제목, 값 꺼내는 함수, y축 범위, 적정 범위 함수, 단위)
CHARTS = [
    ("온도",      lambda s: s.env_state.temperature,   (0, 40),     lambda p: p.temperature_range, "°C"),
    ("습도",      lambda s: s.env_state.humidity,      (20, 100),   lambda p: p.humidity_range, "%"),
    ("토양 습도", lambda s: s.env_state.soil_humidity, (0, 100),    lambda p: p.soil_humidity_range, "%"),
    ("양액 EC",   lambda s: s.env_state.nutrient,      (0, 4),      lambda p: p.nutrient_range, "mS/cm"),
    ("조도",      lambda s: s.env_state.luminosity,    (0, 70000),  lambda p: (p.min_luminosity, 70000), "lux"),
    ("CO2",       lambda s: s.env_state.gas_density,   (150, 1300), lambda p: p.co2_range, "ppm"),
]
