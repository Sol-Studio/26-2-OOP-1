import tkinter as tk
from tkinter import ttk

from core.catalog import ZONES
from ui.theme import COLOR, FONT


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
