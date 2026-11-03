import io, contextlib, re
from collections import deque
import tkinter as tk
from tkinter import ttk, messagebox

from main import PlantProfile, EnvState, PlantState, FarmSection, Farm, LEAFY_STAGES, FRUIT_STAGES

DT = 1 / 6              # 한 단계 = 10분
HISTORY = 6 * 24        # 그래프에 남길 단계 수 (24시간)
FONT = "Malgun Gothic"

COLOR = {
    "bg": "#f3f5f1", "card": "#ffffff", "line": "#c9d3cb", "ink": "#1d2620", "muted": "#6b7a70",
    "healthy": "#2f7d4a", "closed": "#c0582a", "dead": "#7a7a7a", "band": "#e1eee4",
    "night": "#e6e9ef", "plot": "#1f6fb2", "on": "#2f7d4a", "off": "#d9dfda",
    "ready": "#b8860b", "empty": "#f7f8f6",
}

# 작물, 적정 온도, 최소 조도, 적정 토양 습도, 적정 습도, 적정 EC, 재배 일수, 수확량(kg), 생육 단계
PROFILES = [
    ("상추",     (15, 22), 15000, (55, 75), (60, 80), (1.0, 1.6), 6,  4.0,  LEAFY_STAGES),
    ("토마토",   (18, 27), 30000, (60, 80), (60, 80), (2.0, 3.5), 12, 12.0, FRUIT_STAGES),
    ("딸기",     (17, 25), 25000, (55, 75), (60, 75), (0.8, 1.4), 10, 5.0,  FRUIT_STAGES),
    ("파프리카", (20, 27), 30000, (60, 80), (60, 80), (2.0, 3.0), 12, 10.0, FRUIT_STAGES),
    ("오이",     (20, 28), 25000, (65, 85), (70, 90), (1.8, 2.5), 8,  15.0, FRUIT_STAGES),
    ("시금치",   (15, 20), 15000, (55, 75), (60, 80), (1.5, 2.0), 6,  3.0,  LEAFY_STAGES),
]


def make_profile(name):
    _, temp, lux, soil, hum, ec, days, kg, stages = next(p for p in PROFILES if p[0] == name)
    return PlantProfile(name, temp, lux, soil, humidity_range=hum, nutrient_range=ec,
                        grow_days=days, yield_kg=kg, stages=stages)

# 그래프: (제목, 값 꺼내는 함수, y축 범위, 적정 범위 함수, 단위)
CHARTS = [
    ("온도",      lambda s: s.env_state.temperature,   (0, 40),     lambda p: p.temperature_range, "°C"),
    ("습도",      lambda s: s.env_state.humidity,      (20, 100),   lambda p: p.humidity_range, "%"),
    ("토양 습도", lambda s: s.env_state.soil_humidity, (0, 100),    lambda p: p.soil_humidity_range, "%"),
    ("양액 EC",   lambda s: s.env_state.nutrient,      (0, 4),      lambda p: p.nutrient_range, "mS/cm"),
    ("조도",      lambda s: s.env_state.luminosity,    (0, 70000),  lambda p: (p.min_luminosity, 70000), "lux"),
    ("CO2",       lambda s: s.env_state.gas_density,   (150, 1300), lambda p: p.co2_range, "ppm"),
]


def make_farm():
    sections = []
    for i, (name, temp, _, soil, hum, ec, *_) in enumerate(PROFILES):
        env = EnvState(make_profile(name), sum(temp) / 2, sum(hum) / 2, 500, sum(soil) / 2, 0, sum(ec) / 2)
        sections.append(FarmSection(env, PlantState(True, False), False, name=f"구역{i + 1}"))
    return Farm(sections, start_hour=6)


ZONES = [f"구역{i + 1}" for i in range(len(PROFILES))]


class SimulatorWindow(tk.Toplevel):
    """시뮬레이션 환경 조작 창: 진행 제어, 날씨, 병충해 발생. 스마트팜 관리 패널과 따로 띄운다."""
    WEATHER = [("평년", 0), ("한파 (바깥 -10°C)", -10), ("폭염 (바깥 +12°C)", 12)]

    def __init__(self, app):
        super().__init__(app.root, bg=COLOR["bg"], padx=14, pady=12)
        self.app = app
        self.title("에버그로우 - 시뮬레이터")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.withdraw)   # 닫아도 관리 패널에서 다시 열 수 있게 숨기기만

        def section(text):
            frame = tk.LabelFrame(self, text=text, bg=COLOR["bg"], font=(FONT, 9, "bold"), padx=8, pady=6)
            frame.pack(fill="x", pady=(0, 8))
            return frame

        self.status = tk.Label(self, bg=COLOR["bg"], font=(FONT, 10), anchor="w", justify="left")
        self.status.pack(fill="x", pady=(0, 8))

        run = section("진행")
        self.run_btn = ttk.Button(run, text="⏸ 정지", command=app.toggle)
        self.run_btn.pack(side="left")
        ttk.Button(run, text="10분 진행", command=app.step).pack(side="left", padx=4)
        ttk.Button(run, text="초기화", command=app.reset).pack(side="left")
        speed = section("속도 (ms / 10분)")
        self.speed = tk.Scale(speed, from_=20, to=1000, orient="horizontal", length=260,
                              bg=COLOR["bg"], highlightthickness=0)
        self.speed.set(120)
        self.speed.pack(fill="x")

        weather = section("바깥 날씨")
        self.weather = tk.IntVar(value=0)
        for text, delta in self.WEATHER:
            tk.Radiobutton(weather, text=text, value=delta, variable=self.weather, font=(FONT, 9),
                           bg=COLOR["bg"], activebackground=COLOR["bg"],
                           command=lambda: app.set_weather(self.weather.get())).pack(anchor="w")

        pests = section("병충해 발생")
        self.zone = ttk.Combobox(pests, values=ZONES, state="readonly", width=8)
        self.zone.current(0)
        self.zone.pack(side="left")
        ttk.Button(pests, text="🐛 병충해 발생", command=lambda: app.inject_pests(self.zone.current())
                   ).pack(side="left", padx=4)

        # 관리 패널과 겹치지 않게 화면 오른쪽 위에 둔다
        self.update_idletasks()
        self.geometry(f"+{self.winfo_screenwidth() - self.winfo_reqwidth() - 60}+60")

    def refresh(self):
        f, w = self.app.farm, self.app.farm.weather
        mode = next(text for text, delta in self.WEATHER if delta == self.weather.get()).split(" ")[0]
        self.status.config(text=f"Day {f.day}  {int(f.hour):02d}:{int(f.hour % 1 * 60):02d}   "
                                f"바깥 {w.temperature:.1f}°C ({mode})")


class App:
    W, H = 1200, 720

    def __init__(self, root):
        self.root = root
        root.title("에버그로우 스마트팜 - 실시간 시뮬레이션")
        root.configure(bg=COLOR["bg"])

        self.canvas = tk.Canvas(root, width=self.W, height=self.H, bg=COLOR["bg"], highlightthickness=0)
        self.canvas.pack(padx=12, pady=(12, 6))
        self.canvas.bind("<Button-1>", self.on_click)

        bar2 = tk.Frame(root, bg=COLOR["bg"])
        bar2.pack(fill="x", padx=12)
        tk.Label(bar2, text="선택 구역 작물", bg=COLOR["bg"], font=(FONT, 9)).pack(side="left", padx=(0, 4))
        self.crop = ttk.Combobox(bar2, values=[p[0] for p in PROFILES], state="readonly", width=8)
        self.crop.current(0)
        self.crop.pack(side="left")
        ttk.Button(bar2, text="🌱 심기", command=self.plant).pack(side="left", padx=4)
        ttk.Button(bar2, text="🧺 수확 / 정리", command=self.harvest).pack(side="left")
        ttk.Button(bar2, text="수확 가능한 구역 모두 수확", command=self.harvest_all).pack(side="left", padx=4)
        ttk.Button(bar2, text="🚜 갈아엎기", command=self.plow).pack(side="left")
        ttk.Button(bar2, text="⚙ 시뮬레이터 창", command=self.show_simulator).pack(side="right")

        # 로그: 구역별로 걸러 보기 (구역 표시가 없는 날씨 등 공통 로그는 항상 보인다)
        logbar = tk.Frame(root, bg=COLOR["bg"])
        logbar.pack(fill="x", padx=12, pady=(6, 0))
        tk.Label(logbar, text="로그", bg=COLOR["bg"], font=(FONT, 9, "bold")).pack(side="left", padx=(0, 6))
        self.log_filter = tk.StringVar(value="전체")
        for name in ["전체"] + ZONES:
            ttk.Radiobutton(logbar, text=name, value=name, variable=self.log_filter, style="Toolbutton",
                            command=self.refill_log).pack(side="left", padx=1)
        self.entries = deque(maxlen=3000)     # (구역, 글, 경고 여부)

        self.log = tk.Listbox(root, height=7, font=(FONT, 9), bg="#18201b", fg="#d6e6d9",
                              selectbackground="#2f6b45", borderwidth=0, highlightthickness=0)
        self.log.pack(fill="both", expand=True, padx=12, pady=(4, 12))

        self.sim = SimulatorWindow(self)
        self.running = True
        self.reset()
        self.loop()

    # ---------- 상태 ----------
    def reset(self):
        self.farm = make_farm()
        self.selected = 0
        self.history = [deque(maxlen=HISTORY) for _ in self.farm.sections]
        self.night = deque(maxlen=HISTORY)
        self.entries.clear()
        self.log.delete(0, "end")
        self.sim.weather.set(0)
        self.record()
        self.draw()

    def toggle(self):
        self.running = not self.running
        self.sim.run_btn.config(text="⏸ 정지" if self.running else "▶ 시작")
        if self.running:
            self.loop()

    def loop(self):
        if not self.running:
            return
        self.step()
        self.root.after(self.sim.speed.get(), self.loop)

    def show_simulator(self):
        self.sim.deiconify()
        self.sim.lift()

    def step(self):
        self.run(lambda: self.farm.process(DT))
        self.record()
        self.draw()

    def run(self, action):
        """모델 함수를 실행하고, 그동안 찍힌 로그를 로그 창으로 옮긴다."""
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            action()
        stamp = f"Day{self.farm.day} {int(self.farm.hour):02d}:{int(self.farm.hour % 1 * 60):02d}"
        for line in buf.getvalue().splitlines():
            warn = any(k in line for k in ("병충해", "죽었", "격리", "없습니다", "실패", "갈아엎"))
            self.write(f"{stamp}  {line}", warn)

    def plant(self):
        s = self.farm.sections[self.selected]
        self.run(lambda: s.plant(make_profile(self.crop.get())))
        self.draw()

    def harvest(self):
        self.run(lambda: self.farm.harvest(self.farm.sections[self.selected]))
        self.draw()

    def plow(self):
        s = self.farm.sections[self.selected]
        ps = s.plant_state
        if ps and ps.alive and not messagebox.askyesno(
                "갈아엎기", f"{s.label}의 작물(생장 {ps.growth:.0f}%)을 수확 없이 모두 갈아엎을까요?"):
            return
        self.run(s.plow)
        self.draw()

    def harvest_all(self):
        ready = [s for s in self.farm.sections if s.plant_state and s.plant_state.ready]
        if not ready:
            self.write("※ 수확할 수 있는 구역이 없습니다.")
        for s in ready:
            self.run(lambda: self.farm.harvest(s))
        self.draw()

    def record(self):
        for hist, s in zip(self.history, self.farm.sections):
            hist.append([f(s) for _, f, *_ in CHARTS])
        self.night.append(not (6 <= self.farm.hour < 18))

    def inject_pests(self, index):
        s = self.farm.sections[index]
        if not (s.plant_state and s.plant_state.alive):
            self.write(f"※ {s.label}에는 살아 있는 작물이 없습니다.")
            return
        s.plant_state.pests = True
        self.write(f"※ 시뮬레이터: {s.label}에 병충해 발생", True)
        self.draw()

    def set_weather(self, delta):
        self.farm.weather.base_temp = 12 + delta
        self.write(f"※ 시뮬레이터: 바깥 평균기온 {12 + delta:.0f}°C" + (" (평년)" if not delta else ""))
        self.draw()

    def write(self, text, warn=False):
        m = re.search(r"구역\d+", text)
        entry = (m.group() if m else None, text, warn)
        self.entries.append(entry)
        if self.shows(entry[0]):
            self.add_log_line(entry)
            if self.log.size() > 500:
                self.log.delete(0)
            self.log.see("end")

    def shows(self, zone):
        f = self.log_filter.get()
        return f == "전체" or zone is None or zone == f

    def add_log_line(self, entry):
        _, text, warn = entry
        self.log.insert("end", text)
        if warn:
            self.log.itemconfig("end", fg="#f4a97c")

    def refill_log(self):
        self.log.delete(0, "end")
        for entry in [e for e in self.entries if self.shows(e[0])][-500:]:
            self.add_log_line(entry)
        self.log.see("end")

    def on_click(self, e):
        for i, (x1, y1, x2, y2) in enumerate(self.card_boxes):
            if x1 <= e.x <= x2 and y1 <= e.y <= y2:
                self.selected = i
                self.crop.set(self.farm.sections[i].env_state.plant_profile.species)
                self.sim.zone.current(i)
                if self.log_filter.get() != "전체":     # 구역 로그를 보는 중이면 클릭한 구역으로 바꾼다
                    self.log_filter.set(ZONES[i])
                    self.refill_log()
                self.draw()

    # ---------- 그리기 ----------
    def draw(self):
        self.canvas.delete("all")
        self.draw_header()
        self.draw_sections()
        self.draw_harvests()
        self.draw_detail()
        self.sim.refresh()

    def draw_header(self):
        c, f, w = self.canvas, self.farm, self.farm.weather
        h = f.hour
        c.create_text(16, 20, anchor="w", font=(FONT, 15, "bold"), fill=COLOR["ink"],
                      text=f"Day {f.day}  {int(h):02d}:{int(h % 1 * 60):02d}")
        sky = "밤" if w.sunlight <= 0 else ("흐림" if w.cloud > 0.5 else "맑음")
        c.create_text(170, 20, anchor="w", font=(FONT, 10), fill=COLOR["muted"],
                      text=f"바깥  {w.temperature:.1f}°C · 습도 {w.humidity:.0f}% · 햇빛 {w.sunlight:,.0f}lux · {sky}")
        # 하루 진행 막대 (낮/밤)
        x0, x1, y = 16, 560, 44
        c.create_rectangle(x0, y, x1, y + 6, fill=COLOR["night"], outline="")
        c.create_rectangle(x0 + (x1 - x0) * 6 / 24, y, x0 + (x1 - x0) * 18 / 24, y + 6, fill="#f5dc8a", outline="")
        cx = x0 + (x1 - x0) * h / 24
        c.create_oval(cx - 5, y - 2, cx + 5, y + 8, fill=COLOR["ink"], outline="")

    def status(self, s):
        if not s.plant_state:
            return "파종 대기", COLOR["muted"]
        if not s.plant_state.alive:
            return "고사", COLOR["dead"]
        if s.is_closed:
            if s.control_failures:
                return f"방제 실패 {s.control_failures}회", COLOR["closed"]
            return "격리·방제 중", COLOR["closed"]
        if s.plant_state.ready:
            return "수확 가능", COLOR["ready"]
        return "정상", COLOR["healthy"]

    def draw_sections(self):
        c = self.canvas
        cw, ch, gap, ox, oy = 176, 176, 10, 16, 66
        self.card_boxes = []
        for i, s in enumerate(self.farm.sections):
            col, row = i % 3, i // 3
            x1, y1 = ox + col * (cw + gap), oy + row * (ch + gap)
            x2, y2 = x1 + cw, y1 + ch
            self.card_boxes.append((x1, y1, x2, y2))
            label, color = self.status(s)
            ps = s.plant_state
            fill = ("#fbe6da" if s.is_closed else COLOR["empty"] if not ps
                    else "#eeeeee" if not ps.alive else COLOR["card"])
            sel = i == self.selected
            c.create_rectangle(x1, y1, x2, y2, fill=fill, outline=COLOR["plot"] if sel else COLOR["line"],
                               width=3 if sel else 1)
            c.create_text(x1 + 10, y1 + 16, anchor="w", text=s.label, font=(FONT, 10, "bold"), fill=COLOR["ink"])
            c.create_text(x2 - 10, y1 + 16, anchor="e", text=label, font=(FONT, 8, "bold"), fill=color)

            e, p = s.env_state, s.env_state.plant_profile
            rows = [("온도", e.temperature, p.temperature_range, f"{e.temperature:.1f}°"),
                    ("습도", e.humidity, p.humidity_range, f"{e.humidity:.0f}%"),
                    ("토양", e.soil_humidity, p.soil_humidity_range, f"{e.soil_humidity:.0f}%"),
                    ("EC", e.nutrient, p.nutrient_range, f"{e.nutrient:.2f}")]
            for j, (name, v, (lo, hi), txt) in enumerate(rows):
                yy = y1 + 38 + j * 17
                ok = lo <= v <= hi
                c.create_text(x1 + 10, yy, anchor="w", text=name, font=(FONT, 8), fill=COLOR["muted"])
                c.create_text(x2 - 10, yy, anchor="e", text=txt, font=("Consolas", 9),
                              fill=COLOR["ink"] if ok else COLOR["closed"])
                c.create_text(x1 + 50, yy, anchor="w", text=f"{lo:g}~{hi:g}", font=("Consolas", 8), fill=COLOR["muted"])

            if not ps:
                c.create_text(x1 + cw / 2, y1 + 120, text="비어 있음 · 작물을 골라 심기",
                              font=(FONT, 8), fill=COLOR["muted"])
            else:
                grow_col = COLOR["ready"] if ps.ready else COLOR["plot"]
                bars = [("건강", ps.health, color), (p.stage(ps.growth), ps.growth, grow_col)]
                for j, (name, v, col_) in enumerate(bars):
                    yy = y1 + 112 + j * 16
                    c.create_text(x1 + 10, yy, anchor="w", text=name, font=(FONT, 8), fill=COLOR["muted"])
                    c.create_rectangle(x1 + 64, yy - 3, x2 - 38, yy + 3, fill=COLOR["off"], outline="")
                    c.create_rectangle(x1 + 64, yy - 3, x1 + 64 + (cw - 102) * v / 100, yy + 3, fill=col_, outline="")
                    c.create_text(x2 - 10, yy, anchor="e", text=f"{v:.0f}", font=("Consolas", 8), fill=COLOR["ink"])
            self.draw_devices(s.devices, x1 + 10, y1 + 152, small=True)

        c.create_text(16, oy + 2 * (ch + gap) + 4, anchor="nw", font=(FONT, 9), fill=COLOR["muted"],
                      text="카드를 클릭하면 오른쪽에 그 구역의 생육 단계와 24시간 그래프가 나옵니다.\n"
                           "빨간 값은 적정 범위를 벗어난 값입니다.")

    def draw_harvests(self):
        c, log = self.canvas, self.farm.harvests
        x1, x2, y = 16, 560, 498
        total = sum(kg for *_, kg, _ in log)
        c.create_text(x1, y, anchor="w", text="수확 기록", font=(FONT, 11, "bold"), fill=COLOR["ink"])
        c.create_text(x2, y, anchor="e", font=(FONT, 9), fill=COLOR["muted"],
                      text=f"총 {len(log)}회 · {total:.1f}kg")
        c.create_line(x1, y + 14, x2, y + 14, fill=COLOR["line"])
        if not log:
            c.create_text(x1, y + 32, anchor="w", font=(FONT, 9), fill=COLOR["muted"],
                          text="아직 수확한 작물이 없습니다. 카드가 '수확 가능'이 되면 수확하세요.")
            return
        cols = [(x1, "w", "일차"), (x1 + 60, "w", "구역"), (x1 + 130, "w", "작물"),
                (x1 + 300, "e", "수확량"), (x1 + 400, "e", "품질")]
        for x, anchor, text in cols:
            c.create_text(x, y + 28, anchor=anchor, text=text, font=(FONT, 8, "bold"), fill=COLOR["muted"])
        for k, (day, zone, crop, kg, quality) in enumerate(reversed(log[-10:])):
            yy = y + 46 + k * 18
            row = [f"Day {day}", zone, crop, f"{kg:.1f} kg", f"{quality:.0f}%"]
            for (x, anchor, _), text in zip(cols, row):
                c.create_text(x, yy, anchor=anchor, text=text, font=(FONT, 9), fill=COLOR["ink"])
            c.create_rectangle(x1 + 410, yy - 3, x1 + 410 + 1.2 * quality, yy + 3, outline="",
                               fill=COLOR["healthy"] if quality >= 70 else COLOR["closed"])

    def draw_devices(self, d, x, y, small=False):
        c = self.canvas
        items = [("난방", d.heater), ("냉방", d.cooler), ("환기", d.fan), ("가습", d.humidifier),
                 ("제습", d.dehumidifier), (f"조명{int(d.light * 100)}%" if d.light else "조명", d.light > 0),
                 ("급수", d.water_l > 0), ("비료", d.fertilizer_g > 0)]
        w = 19 if small else 62
        for k, (name, on) in enumerate(items):
            xx = x + k * (w + 1)
            if small:
                c.create_rectangle(xx, y - 7, xx + w - 2, y + 7, fill=COLOR["on"] if on else COLOR["off"], outline="")
                c.create_text(xx + w / 2 - 1, y, text=name[0], font=(FONT, 7, "bold"),
                              fill="#ffffff" if on else COLOR["muted"])
            else:
                c.create_rectangle(xx, y - 11, xx + w - 4, y + 11, fill=COLOR["on"] if on else COLOR["off"], outline="")
                c.create_text(xx + (w - 4) / 2, y, text=name, font=(FONT, 8, "bold"),
                              fill="#ffffff" if on else COLOR["muted"])

    def draw_detail(self):
        c = self.canvas
        s = self.farm.sections[self.selected]
        d, p = s.devices, s.env_state.plant_profile
        ox = 590
        c.create_text(ox, 20, anchor="w", text=f"{s.label}  상세", font=(FONT, 13, "bold"), fill=COLOR["ink"])
        c.create_text(self.W - 10, 20, anchor="e", font=(FONT, 9), fill=COLOR["muted"],
                      text=f"누적  물 {d.total_water_l:.0f}L · 비료 {d.total_fertilizer_g:.0f}g · "
                           f"전력 {d.total_energy_kwh:.1f}kWh (현재 {d.power_kw():.1f}kW)")
        self.draw_devices(d, ox, 48)
        self.draw_growth(s, ox, 82)

        hist = self.history[self.selected]
        gw, gh, gx, gy = 290, 162, 18, 22
        for k, (title, _, (lo, hi), band, unit) in enumerate(CHARTS):
            col, row = k % 2, k // 2
            x1 = ox + col * (gw + gx)
            y1 = 156 + row * (gh + gy)
            x2, y2 = x1 + gw, y1 + gh
            top, bot = y1 + 18, y2 - 4
            ymap = lambda v: bot - (min(max(v, lo), hi) - lo) / (hi - lo) * (bot - top)
            xstep = gw / (HISTORY - 1)

            c.create_rectangle(x1, top, x2, bot, fill=COLOR["card"], outline=COLOR["line"])
            # 밤 구간 음영
            for i, night in enumerate(self.night):
                if night:
                    c.create_rectangle(x1 + i * xstep, top + 1, x1 + (i + 1) * xstep, bot - 1,
                                       fill=COLOR["night"], outline="")
            b_lo, b_hi = band(p)
            c.create_rectangle(x1 + 1, ymap(b_hi), x2 - 1, ymap(b_lo), fill=COLOR["band"], outline="")
            for v in (lo, hi):
                c.create_text(x1 - 3, ymap(v), anchor="e", text=f"{v:g}", font=("Consolas", 7), fill=COLOR["muted"])

            pts = [(x1 + i * xstep, ymap(h[k])) for i, h in enumerate(hist)]
            if len(pts) > 1:
                c.create_line(*[v for pt in pts for v in pt], fill=COLOR["plot"], width=2)
            cur = hist[-1][k]
            ok = b_lo <= cur <= b_hi
            if pts:
                c.create_oval(pts[-1][0] - 3, pts[-1][1] - 3, pts[-1][0] + 3, pts[-1][1] + 3,
                              fill=COLOR["plot"] if ok else COLOR["closed"], outline="")
            c.create_text(x1, y1 + 6, anchor="w", text=title, font=(FONT, 9, "bold"), fill=COLOR["ink"])
            val = f"{cur:,.0f}" if hi >= 1000 else (f"{cur:.2f}" if hi < 10 else f"{cur:.1f}")
            c.create_text(x2, y1 + 6, anchor="e", text=f"{val} {unit}", font=("Consolas", 9, "bold"),
                          fill=COLOR["ink"] if ok else COLOR["closed"])

        c.create_text(ox, self.H - 2, anchor="sw", font=(FONT, 8), fill=COLOR["muted"],
                      text="최근 24시간 · 초록 띠 = 적정 범위 · 회색 = 밤")

    def draw_growth(self, s, ox, y):
        """생육 단계 타임라인: 단계별 구간, 현재 생장도, 수확 예상"""
        c, ps, p = self.canvas, s.plant_state, s.env_state.plant_profile
        x1, x2 = ox, self.W - 10
        top, bot = y + 18, y + 32
        c.create_text(x1, y, anchor="w", text="생육 단계", font=(FONT, 10, "bold"), fill=COLOR["ink"])
        if not ps:
            c.create_rectangle(x1, top, x2, bot, fill=COLOR["off"], outline="")
            c.create_text(x1 + 70, y, anchor="w", font=(FONT, 9), fill=COLOR["muted"],
                          text="빈 구역 · 작물을 고르고 '심기'를 누르세요")
            return

        xmap = lambda g: x1 + (x2 - x1) * g / 100
        current = p.stage(ps.growth)
        fill = COLOR["dead"] if not ps.alive else COLOR["ready"] if ps.ready else COLOR["healthy"]
        c.create_rectangle(x1, top, x2, bot, fill=COLOR["off"], outline="")
        c.create_rectangle(x1, top, xmap(ps.growth), bot, fill=fill, outline="")
        stages = p.stages
        for k, (name, start) in enumerate(stages[:-1]):
            end = stages[k + 1][1]
            if k:
                c.create_line(xmap(start), top - 3, xmap(start), bot + 3, fill=COLOR["card"], width=2)
            c.create_text((xmap(start) + xmap(end)) / 2, bot + 10, text=name,
                          font=(FONT, 8, "bold" if name == current else "normal"),
                          fill=COLOR["ink"] if name == current else COLOR["muted"])
        c.create_text(x2, bot + 10, anchor="e", text=stages[-1][0],
                      font=(FONT, 8, "bold" if ps.ready else "normal"),
                      fill=COLOR["ready"] if ps.ready else COLOR["muted"])
        mx = xmap(ps.growth)
        c.create_polygon(mx - 5, top - 9, mx + 5, top - 9, mx, top - 2, fill=COLOR["ink"], outline="")

        # 요약 줄
        if not ps.alive:
            info, col = "고사 · '수확 / 정리'로 비우세요", COLOR["dead"]
        elif ps.ready:
            info, col = "수확 가능 · 늦으면 상합니다", COLOR["ready"]
        else:
            left = ps.hours_to_harvest()
            info = "수확까지 계산 중" if left is None else f"수확까지 약 {left / 24:.1f}일"
            col = COLOR["ink"]
        c.create_text(x1 + 70, y, anchor="w", font=(FONT, 9), fill=col,
                      text=f"{current} {ps.growth:.0f}% · {info}")
        c.create_text(x2, y, anchor="e", font=(FONT, 9), fill=COLOR["muted"],
                      text=f"파종 후 {ps.age_hours / 24:.1f}일 · 평균 건강 {ps.avg_health:.0f} · "
                           f"예상 수확량 {p.yield_kg * ps.avg_health / 100:.1f}kg")


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
