import tkinter as tk
from tkinter import ttk

from common import COLOR, FONT, PROFILES

CROP_COLORS = ["#2f7d4a", "#d63a2f", "#e0405a", "#e8a91c", "#1f6fb2", "#7a4fb0"]
STEPS_PER_DAY = 144
MAX_POINTS = 360          # 선 하나에 그릴 최대 점 수 (기간이 길면 솎아서 그린다)


class PriceWindow(tk.Toplevel):
    """작물별 시세 그래프. 기간(1일·7일·30일)을 골라 본다."""
    W, H = 820, 430
    PLOT = (70, 24, 600, 370)      # 그래프 영역 x1, y1, x2, y2

    def __init__(self, app):
        super().__init__(app.root, bg=COLOR["bg"], padx=10, pady=10)
        self.app = app
        self.title("에버그로우 - 작물 시세")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.withdraw)   # 닫아도 관리 패널에서 다시 열 수 있게 숨기기만

        bar = tk.Frame(self, bg=COLOR["bg"])
        bar.pack(fill="x", pady=(0, 6))
        tk.Label(bar, text="기간", bg=COLOR["bg"], font=(FONT, 9, "bold")).pack(side="left", padx=(0, 6))
        self.days = tk.IntVar(value=7)
        for d in (1, 7, 30):
            ttk.Radiobutton(bar, text=f"{d}일", value=d, variable=self.days, style="Toolbutton",
                            command=self.refresh).pack(side="left", padx=1)
        self.canvas = tk.Canvas(self, width=self.W, height=self.H, bg=COLOR["card"], highlightthickness=1,
                                highlightbackground=COLOR["line"])
        self.canvas.pack()
        self.withdraw()

    def refresh(self):
        if self.state() == "withdrawn":
            return
        c, market = self.canvas, self.app.farm.market
        c.delete("all")
        x1, y1, x2, y2 = self.PLOT
        days = self.days.get()
        n = days * STEPS_PER_DAY
        names = [p[0] for p in PROFILES]
        series = {name: list(market.history[name])[-n:] for name in names}
        top = max(max(v) for v in series.values())
        step = 1000 if top < 10000 else 5000
        top = (int(top // step) + 1) * step

        ymap = lambda v: y2 - v / top * (y2 - y1)
        for k in range(0, top + 1, step):
            c.create_line(x1, ymap(k), x2, ymap(k), fill=COLOR["line"] if k else COLOR["muted"])
            c.create_text(x1 - 6, ymap(k), anchor="e", text=f"{k:,}", font=("Consolas", 8), fill=COLOR["muted"])
        c.create_text(x1 - 6, y1 - 12, anchor="e", text="원/kg", font=(FONT, 8), fill=COLOR["muted"])
        for d in range(days + 1):
            if days <= 7 or d % 5 == 0:
                x = x1 + (x2 - x1) * d / days
                c.create_line(x, y2, x, y2 + 4, fill=COLOR["muted"])
                c.create_text(x, y2 + 14, text="지금" if d == days else f"{d - days}일", font=(FONT, 8),
                              fill=COLOR["muted"])

        for name, color in zip(names, CROP_COLORS):
            vals = series[name]
            if len(vals) < 2:
                continue
            stride = max(1, len(vals) // MAX_POINTS)
            idx = list(range(0, len(vals), stride))
            if idx[-1] != len(vals) - 1:
                idx.append(len(vals) - 1)
            # 기록이 기간보다 짧으면 오른쪽 끝(지금)에서부터 그린다
            xs = [x2 - (x2 - x1) * (len(vals) - 1 - i) / (n - 1) for i in idx]
            c.create_line(*[v for xy in zip(xs, [ymap(vals[i]) for i in idx]) for v in xy], fill=color, width=2)

        # 오른쪽: 작물별 현재 시세와 하루 전 대비 변동률
        lx = x2 + 24
        c.create_text(lx, y1 - 12, anchor="w", text="현재 시세", font=(FONT, 9, "bold"), fill=COLOR["ink"])
        full = market.history
        for k, (name, color) in enumerate(zip(names, CROP_COLORS)):
            yy = y1 + 18 + k * 54
            now, base = market.price(name), market.base[name]
            hist = full[name]
            day_ago = hist[-STEPS_PER_DAY] if len(hist) > STEPS_PER_DAY else hist[0]
            change = (now / day_ago - 1) * 100
            c.create_rectangle(lx, yy - 6, lx + 12, yy + 6, fill=color, outline="")
            c.create_text(lx + 20, yy, anchor="w", text=name, font=(FONT, 10, "bold"), fill=COLOR["ink"])
            c.create_text(lx + 20, yy + 20, anchor="w", text=f"{now:,.0f}원", font=("Consolas", 10), fill=COLOR["ink"])
            c.create_text(self.W - 12, yy, anchor="e", font=(FONT, 9, "bold"),
                          text=f"{'▲' if change >= 0 else '▼'} {abs(change):.1f}%",
                          fill=COLOR["closed"] if change >= 0 else COLOR["plot"])
            c.create_text(self.W - 12, yy + 20, anchor="e", text=f"기준 {base:,}", font=(FONT, 8), fill=COLOR["muted"])
        c.create_text(x1, self.H - 12, anchor="w", font=(FONT, 8), fill=COLOR["muted"],
                      text="많이 수확해 팔면 그 작물 시세가 내려가고, 시간이 지나면 기준가로 돌아옵니다. 변동률은 하루 전 대비입니다.")
