import io, contextlib
from collections import deque
import tkinter as tk
from tkinter import messagebox

from core.catalog import DT, make_profile, make_farm
from ui.theme import HISTORY, COLOR, CHARTS
from ui.cctv.window import CctvWindow
from ui.main.widgets.control_bar import ControlBar
from ui.main.widgets.detail_panel import draw_detail
from ui.main.widgets.harvest_log import draw_harvests
from ui.main.widgets.header import draw_header
from ui.main.widgets.log_panel import LogPanel
from ui.mobile.window import MobileWindow
from ui.price.window import PriceWindow
from ui.main.widgets.section_cards import draw_section_cards, section_status
from ui.simulator.window import SimulatorWindow


class App:
    W, H = 1200, 720

    def __init__(self, root):
        self.root = root
        root.title("에버그로우 스마트팜 - 실시간 시뮬레이션")
        root.configure(bg=COLOR["bg"])

        self.canvas = tk.Canvas(root, width=self.W, height=self.H, bg=COLOR["bg"], highlightthickness=0)
        self.canvas.pack(padx=12, pady=(12, 6))
        self.canvas.bind("<Button-1>", self.on_click)

        self.controls = ControlBar(root, self)
        self.log = LogPanel(root)

        self.sim = SimulatorWindow(self)
        self.mobile = MobileWindow(self)
        self.cctv = CctvWindow(self)
        self.prices = PriceWindow(self)
        self.running = True
        self.reset()
        self.loop()

    # ---------- 상태 ----------
    def reset(self):
        self.farm = make_farm()
        self.apply_auto_replant()
        self.selected = 0
        self.history = [deque(maxlen=HISTORY) for _ in self.farm.sections]
        self.night = deque(maxlen=HISTORY)
        self.log.clear()
        self.sim.weather.set(0)
        self.record()
        self.draw()

    def apply_auto_replant(self):
        self.farm.auto_replant = self.controls.auto_replant.get()

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

    def show(self, window):
        window.deiconify()
        window.lift()
        window.refresh()

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
        self.run(lambda: s.plant(make_profile(self.controls.crop.get())))
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
        self.log.write(text, warn)

    @property
    def entries(self):
        return self.log.entries

    def status(self, s):
        return section_status(s)

    def on_click(self, e):
        for i, (x1, y1, x2, y2) in enumerate(self.card_boxes):
            if x1 <= e.x <= x2 and y1 <= e.y <= y2:
                self.select(i)

    def select(self, i):
        """구역 선택. 관리 패널, 시뮬레이터, 모바일 앱이 같은 구역을 가리키게 맞춘다."""
        self.selected = i
        self.controls.crop.set(self.farm.sections[i].env_state.plant_profile.species)
        self.sim.zone.current(i)
        self.log.follow_zone(i)
        self.draw()

    # ---------- 그리기 ----------
    def draw(self):
        c = self.canvas
        c.delete("all")
        draw_header(c, self.farm)
        self.card_boxes = draw_section_cards(c, self.farm, self.selected)
        draw_harvests(c, self.farm)
        draw_detail(c, self.farm, self.selected, self.history[self.selected], self.night, self.W)
        self.sim.refresh()
        self.mobile.refresh()
        self.cctv.refresh()
        self.prices.refresh()


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
