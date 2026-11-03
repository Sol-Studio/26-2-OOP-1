import io, contextlib
from collections import deque
import tkinter as tk
from tkinter import ttk

from main import PlantProfile, EnvState, PlantState, FarmSection, Farm

DT = 1 / 6              # 한 단계 = 10분
HISTORY = 6 * 24        # 그래프에 남길 단계 수 (24시간)
FONT = "Malgun Gothic"

COLOR = {
    "bg": "#f3f5f1", "card": "#ffffff", "line": "#c9d3cb", "ink": "#1d2620", "muted": "#6b7a70",
    "healthy": "#2f7d4a", "closed": "#c0582a", "dead": "#7a7a7a", "band": "#e1eee4",
    "night": "#e6e9ef", "plot": "#1f6fb2", "on": "#2f7d4a", "off": "#d9dfda",
}

# 작물, 적정 온도, 최소 조도, 적정 토양 습도, 적정 습도, 적정 EC
PROFILES = [
    ("상추",     (15, 22), 15000, (55, 75), (60, 80), (1.0, 1.6)),
    ("토마토",   (18, 27), 30000, (60, 80), (60, 80), (2.0, 3.5)),
    ("딸기",     (17, 25), 25000, (55, 75), (60, 75), (0.8, 1.4)),
    ("파프리카", (20, 27), 30000, (60, 80), (60, 80), (2.0, 3.0)),
    ("오이",     (20, 28), 25000, (65, 85), (70, 90), (1.8, 2.5)),
    ("시금치",   (15, 20), 15000, (55, 75), (60, 80), (1.5, 2.0)),
]

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
    for i, (name, temp, lux, soil, hum, ec) in enumerate(PROFILES):
        profile = PlantProfile(name, temp, lux, soil, humidity_range=hum, nutrient_range=ec)
        env = EnvState(profile, sum(temp) / 2, sum(hum) / 2, 500, sum(soil) / 2, 0, sum(ec) / 2)
        sections.append(FarmSection(env, PlantState(True, False), False, name=f"구역{i + 1} {name}"))
    return Farm(sections, start_hour=6)


class App:
    W, H = 1200, 660

    def __init__(self, root):
        self.root = root
        root.title("에버그로우 스마트팜 - 실시간 시뮬레이션")
        root.configure(bg=COLOR["bg"])

        self.canvas = tk.Canvas(root, width=self.W, height=self.H, bg=COLOR["bg"], highlightthickness=0)
        self.canvas.pack(padx=12, pady=(12, 6))
        self.canvas.bind("<Button-1>", self.on_click)

        bar = tk.Frame(root, bg=COLOR["bg"])
        bar.pack(fill="x", padx=12)
        self.run_btn = ttk.Button(bar, text="⏸ 정지", command=self.toggle)
        self.run_btn.pack(side="left")
        ttk.Button(bar, text="10분 진행", command=self.step).pack(side="left", padx=4)
        ttk.Button(bar, text="초기화", command=self.reset).pack(side="left")
        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=10)
        ttk.Button(bar, text="선택 구역에 병충해", command=self.inject_pests).pack(side="left")
        ttk.Button(bar, text="한파 (바깥 -10°C)", command=lambda: self.shift_weather(-10)).pack(side="left", padx=4)
        ttk.Button(bar, text="폭염 (바깥 +12°C)", command=lambda: self.shift_weather(12)).pack(side="left")
        tk.Label(bar, text="속도(ms/10분)", bg=COLOR["bg"], font=(FONT, 9)).pack(side="left", padx=(12, 2))
        self.speed = tk.Scale(bar, from_=20, to=1000, orient="horizontal", length=150,
                              bg=COLOR["bg"], highlightthickness=0)
        self.speed.set(120)
        self.speed.pack(side="left")

        self.log = tk.Listbox(root, height=7, font=(FONT, 9), bg="#18201b", fg="#d6e6d9",
                              selectbackground="#2f6b45", borderwidth=0, highlightthickness=0)
        self.log.pack(fill="both", expand=True, padx=12, pady=(6, 12))

        self.running = True
        self.reset()
        self.loop()

    # ---------- 상태 ----------
    def reset(self):
        self.farm = make_farm()
        self.selected = 0
        self.history = [deque(maxlen=HISTORY) for _ in self.farm.sections]
        self.night = deque(maxlen=HISTORY)
        self.log.delete(0, "end")
        self.record()
        self.draw()

    def toggle(self):
        self.running = not self.running
        self.run_btn.config(text="⏸ 정지" if self.running else "▶ 시작")
        if self.running:
            self.loop()

    def loop(self):
        if not self.running:
            return
        self.step()
        self.root.after(self.speed.get(), self.loop)

    def step(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.farm.process(DT)
        stamp = f"Day{self.farm.day} {int(self.farm.hour):02d}:{int(self.farm.hour % 1 * 60):02d}"
        for line in buf.getvalue().splitlines():
            warn = any(k in line for k in ("병충해", "죽었", "격리"))
            self.write(f"{stamp}  {line}", warn)
        self.record()
        self.draw()

    def record(self):
        for hist, s in zip(self.history, self.farm.sections):
            hist.append([f(s) for _, f, *_ in CHARTS])
        self.night.append(not (6 <= self.farm.hour < 18))

    def inject_pests(self):
        s = self.farm.sections[self.selected]
        s.plant_state.pests = True
        self.write(f"※ 사용자: {s.name}에 병충해 발생", True)

    def shift_weather(self, delta):
        w = self.farm.weather
        w.base_temp = 12 + delta if w.base_temp == 12 else 12
        self.write(f"※ 바깥 평균기온 {w.base_temp:.0f}°C로 변경" + (" (원래대로)" if w.base_temp == 12 else ""))

    def write(self, text, warn=False):
        self.log.insert("end", text)
        if warn:
            self.log.itemconfig("end", fg="#f4a97c")
        if self.log.size() > 500:
            self.log.delete(0)
        self.log.see("end")

    def on_click(self, e):
        for i, (x1, y1, x2, y2) in enumerate(self.card_boxes):
            if x1 <= e.x <= x2 and y1 <= e.y <= y2:
                self.selected = i
                self.draw()

    # ---------- 그리기 ----------
    def draw(self):
        self.canvas.delete("all")
        self.draw_header()
        self.draw_sections()
        self.draw_detail()

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
        if not s.plant_state.alive:
            return "고사", COLOR["dead"]
        if s.is_closed:
            return "격리·방제 중", COLOR["closed"]
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
            fill = "#fbe6da" if s.is_closed else ("#eeeeee" if not s.plant_state.alive else COLOR["card"])
            sel = i == self.selected
            c.create_rectangle(x1, y1, x2, y2, fill=fill, outline=COLOR["plot"] if sel else COLOR["line"],
                               width=3 if sel else 1)
            c.create_text(x1 + 10, y1 + 16, anchor="w", text=s.name, font=(FONT, 10, "bold"), fill=COLOR["ink"])
            c.create_text(x2 - 10, y1 + 16, anchor="e", text=label, font=(FONT, 8, "bold"), fill=color)

            e, p, ps = s.env_state, s.env_state.plant_profile, s.plant_state
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

            for j, (name, v, col_) in enumerate([("건강", ps.health, color), ("생장", ps.growth, COLOR["plot"])]):
                yy = y1 + 112 + j * 16
                c.create_text(x1 + 10, yy, anchor="w", text=name, font=(FONT, 8), fill=COLOR["muted"])
                c.create_rectangle(x1 + 40, yy - 3, x2 - 42, yy + 3, fill=COLOR["off"], outline="")
                c.create_rectangle(x1 + 40, yy - 3, x1 + 40 + (cw - 82) * v / 100, yy + 3, fill=col_, outline="")
                c.create_text(x2 - 10, yy, anchor="e", text=f"{v:.0f}", font=("Consolas", 8), fill=COLOR["ink"])
            self.draw_devices(s.devices, x1 + 10, y1 + 152, small=True)

        c.create_text(16, oy + 2 * (ch + gap) + 4, anchor="nw", font=(FONT, 9), fill=COLOR["muted"],
                      text="카드를 클릭하면 오른쪽에 그 구역의 24시간 그래프가 나옵니다. 빨간 값은 적정 범위를 벗어난 값입니다.")

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
        c.create_text(ox, 20, anchor="w", text=f"{s.name}  상세", font=(FONT, 13, "bold"), fill=COLOR["ink"])
        c.create_text(self.W - 10, 20, anchor="e", font=(FONT, 9), fill=COLOR["muted"],
                      text=f"누적  물 {d.total_water_l:.0f}L · 비료 {d.total_fertilizer_g:.0f}g · "
                           f"전력 {d.total_energy_kwh:.1f}kWh (현재 {d.power_kw():.1f}kW)")
        self.draw_devices(d, ox, 48)

        hist = self.history[self.selected]
        gw, gh, gx, gy = 290, 162, 18, 22
        for k, (title, _, (lo, hi), band, unit) in enumerate(CHARTS):
            col, row = k % 2, k // 2
            x1 = ox + col * (gw + gx)
            y1 = 80 + row * (gh + gy)
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

        c.create_text(ox, self.H - 8, anchor="sw", font=(FONT, 8), fill=COLOR["muted"],
                      text="최근 24시간 · 초록 띠 = 적정 범위 · 회색 = 밤")


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
