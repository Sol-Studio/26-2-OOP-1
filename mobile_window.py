import tkinter as tk

from common import COLOR, FONT, CHARTS


class MobileWindow(tk.Toplevel):
    """농장주가 휴대폰으로 보는 앱 화면(9:16). 홈 / 구역 상세 / 알림 세 탭을 오간다."""
    W, H = 360, 640
    BAR, NAV = 26, 56          # 위 상태 표시줄, 아래 탭 바 높이
    TABS = [("home", "홈"), ("zone", "구역"), ("alerts", "알림")]

    def __init__(self, app):
        super().__init__(app.root, bg="#111814")
        self.app = app
        self.tab = "home"
        self.buttons = []      # ((x1, y1, x2, y2), 누르면 할 일)
        self.title("에버그로우 - 모바일")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.withdraw)   # 닫아도 관리 패널에서 다시 열 수 있게 숨기기만

        self.canvas = tk.Canvas(self, width=self.W, height=self.H, bg=COLOR["bg"], highlightthickness=0)
        self.canvas.pack(padx=8, pady=8)
        self.canvas.bind("<Button-1>", self.on_click)

        # 관리 패널·시뮬레이터와 겹치지 않게 화면 오른쪽 아래에 둔다
        self.update_idletasks()
        x = self.winfo_screenwidth() - self.winfo_reqwidth() - 60
        y = max(0, self.winfo_screenheight() - self.winfo_reqheight() - 80)
        self.geometry(f"+{x}+{y}")

    # ---------- 입력 ----------
    def button(self, box, action):
        self.buttons.append((box, action))

    def on_click(self, e):
        for (x1, y1, x2, y2), action in self.buttons:
            if x1 <= e.x <= x2 and y1 <= e.y <= y2:
                action()
                return

    def go(self, tab):
        self.tab = tab
        self.refresh()

    def open_zone(self, i):
        self.tab = "zone"
        self.app.select(i)     # 선택이 바뀌면 관리 패널이 다시 그리면서 이 창도 새로 그린다

    # ---------- 그리기 ----------
    def refresh(self):
        if self.state() == "withdrawn":
            return
        self.canvas.delete("all")
        self.buttons = []
        self.draw_status_bar()
        {"home": self.draw_home, "zone": self.draw_zone, "alerts": self.draw_alerts}[self.tab]()
        self.draw_nav()

    def draw_status_bar(self):
        c, f = self.canvas, self.app.farm
        c.create_rectangle(0, 0, self.W, self.BAR, fill="#18201b", outline="")
        c.create_text(16, self.BAR / 2, anchor="w", font=(FONT, 9, "bold"), fill="#ffffff",
                      text=f"{int(f.hour):02d}:{int(f.hour % 1 * 60):02d}")
        c.create_text(self.W - 16, self.BAR / 2, anchor="e", font=(FONT, 8), fill="#d6e6d9", text="EverGrow")

    def draw_nav(self):
        c, top = self.canvas, self.H - self.NAV
        c.create_rectangle(0, top, self.W, self.H, fill=COLOR["card"], outline="")
        c.create_line(0, top, self.W, top, fill=COLOR["line"])
        warns = sum(1 for _, _, warn in self.app.entries if warn)
        w = self.W / len(self.TABS)
        for k, (key, name) in enumerate(self.TABS):
            x1 = k * w
            on = key == self.tab
            if on:
                c.create_rectangle(x1 + w / 2 - 18, top + 6, x1 + w / 2 + 18, top + 9, fill=COLOR["healthy"], outline="")
            c.create_text(x1 + w / 2, top + self.NAV / 2 + 2, text=name, font=(FONT, 10, "bold" if on else "normal"),
                          fill=COLOR["healthy"] if on else COLOR["muted"])
            if key == "alerts" and warns:
                c.create_oval(x1 + w / 2 + 20, top + 12, x1 + w / 2 + 38, top + 28, fill=COLOR["closed"], outline="")
                c.create_text(x1 + w / 2 + 29, top + 20, text=str(min(warns, 99)), font=(FONT, 7, "bold"), fill="#ffffff")
            self.button((x1, top, x1 + w, self.H), lambda key=key: self.go(key))

    def header(self, title, sub):
        c, y = self.canvas, self.BAR + 14
        c.create_text(16, y + 10, anchor="w", text=title, font=(FONT, 16, "bold"), fill=COLOR["ink"])
        c.create_text(16, y + 36, anchor="w", text=sub, font=(FONT, 9), fill=COLOR["muted"])
        return y + 56

    def bar(self, x1, x2, y, value, color, h=6):
        self.canvas.create_rectangle(x1, y, x2, y + h, fill=COLOR["off"], outline="")
        self.canvas.create_rectangle(x1, y, x1 + (x2 - x1) * value / 100, y + h, fill=color, outline="")

    def draw_home(self):
        c, f, w = self.canvas, self.app.farm, self.app.farm.weather
        sky = "밤" if w.sunlight <= 0 else ("흐림" if w.cloud > 0.5 else "맑음")
        y = self.header("우리 농장", f"Day {f.day} · 바깥 {w.temperature:.1f}°C {sky} · 습도 {w.humidity:.0f}%")

        # 요약 칩: 수확 가능 / 주의 / 정상
        states = [self.app.status(s) for s in f.sections]
        ready = sum(1 for label, _ in states if label == "수확 가능")
        alert = sum(1 for _, col in states if col in (COLOR["closed"], COLOR["dead"]))
        chips = [("수확 가능", ready, COLOR["ready"]), ("주의", alert, COLOR["closed"]),
                 ("전체 구역", len(states), COLOR["healthy"])]
        cw = (self.W - 32 - 16) / 3
        for k, (name, n, col) in enumerate(chips):
            x1 = 16 + k * (cw + 8)
            c.create_rectangle(x1, y, x1 + cw, y + 50, fill=COLOR["card"], outline=COLOR["line"])
            c.create_text(x1 + 10, y + 16, anchor="w", text=name, font=(FONT, 8), fill=COLOR["muted"])
            c.create_text(x1 + 10, y + 36, anchor="w", text=str(n), font=(FONT, 14, "bold"), fill=col)
        y += 62

        # 구역 목록: 누르면 구역 탭으로
        ch = (self.H - self.NAV - 10 - y) / len(f.sections)
        for i, s in enumerate(f.sections):
            y1, y2 = y + i * ch, y + (i + 1) * ch - 6
            label, col = self.app.status(s)
            ps, e = s.plant_state, s.env_state
            sel = i == self.app.selected
            c.create_rectangle(16, y1, self.W - 16, y2, fill=COLOR["card"],
                               outline=COLOR["plot"] if sel else COLOR["line"], width=2 if sel else 1)
            c.create_rectangle(16, y1, 21, y2, fill=col, outline="")
            c.create_text(32, y1 + 14, anchor="w", text=s.label, font=(FONT, 10, "bold"), fill=COLOR["ink"])
            c.create_text(self.W - 28, y1 + 14, anchor="e", text=f"{label}  ›", font=(FONT, 8, "bold"), fill=col)
            if ps:
                c.create_text(32, y2 - 12, anchor="w", font=("Consolas", 8), fill=COLOR["muted"],
                              text=f"{e.temperature:.1f}°  {e.humidity:.0f}%  {ps.growth:3.0f}%")
                self.bar(170, self.W - 28, y2 - 15, ps.growth, COLOR["ready"] if ps.ready else COLOR["plot"])
            else:
                c.create_text(32, y2 - 12, anchor="w", text="비어 있음", font=(FONT, 8), fill=COLOR["muted"])
            self.button((16, y1, self.W - 16, y2), lambda i=i: self.open_zone(i))

    def draw_zone(self):
        c, app = self.canvas, self.app
        s = app.farm.sections[app.selected]
        ps, e, p, d = s.plant_state, s.env_state, s.env_state.plant_profile, s.devices
        label, col = app.status(s)
        y = self.header(f"‹ {s.label}", "")
        self.button((0, self.BAR, 200, y - 28), lambda: self.go("home"))
        c.create_text(16, y - 20, anchor="w", text=label, font=(FONT, 9, "bold"), fill=col)

        # 생육 카드
        c.create_rectangle(16, y, self.W - 16, y + 84, fill=COLOR["card"], outline=COLOR["line"])
        if ps:
            left = ps.hours_to_harvest()
            info = ("고사" if not ps.alive else "수확 가능" if ps.ready
                    else "계산 중" if left is None else f"수확까지 {left / 24:.1f}일")
            c.create_text(28, y + 16, anchor="w", text=p.stage(ps.growth), font=(FONT, 11, "bold"), fill=COLOR["ink"])
            c.create_text(self.W - 28, y + 16, anchor="e", text=info, font=(FONT, 9), fill=COLOR["muted"])
            for j, (name, v, bc) in enumerate([("생장", ps.growth, COLOR["ready"] if ps.ready else COLOR["plot"]),
                                               ("건강", ps.health, col)]):
                yy = y + 42 + j * 22
                c.create_text(28, yy, anchor="w", text=name, font=(FONT, 8), fill=COLOR["muted"])
                self.bar(66, self.W - 64, yy - 3, v, bc)
                c.create_text(self.W - 28, yy, anchor="e", text=f"{v:.0f}%", font=("Consolas", 9), fill=COLOR["ink"])
        else:
            c.create_text(self.W / 2, y + 42, text="빈 구역입니다.\n관리 패널에서 작물을 심으세요.",
                          font=(FONT, 9), fill=COLOR["muted"], justify="center")
        y += 96

        # 환경 값 2열 x 3줄 (적정 범위를 벗어나면 빨간색)
        tw, th = (self.W - 32 - 8) / 2, 52
        for k, (title, get, (_, hi), band, unit) in enumerate(CHARTS):
            x1, y1 = 16 + (k % 2) * (tw + 8), y + (k // 2) * (th + 8)
            v, (b_lo, b_hi) = get(s), band(p)
            ok = b_lo <= v <= b_hi
            val = f"{v:,.0f}" if hi >= 1000 else (f"{v:.2f}" if hi < 10 else f"{v:.1f}")
            c.create_rectangle(x1, y1, x1 + tw, y1 + th, fill=COLOR["card"], outline=COLOR["line"])
            c.create_text(x1 + 10, y1 + 14, anchor="w", text=title, font=(FONT, 8), fill=COLOR["muted"])
            c.create_text(x1 + tw - 10, y1 + 14, anchor="e", text=unit, font=(FONT, 7), fill=COLOR["muted"])
            c.create_text(x1 + 10, y1 + 36, anchor="w", text=val, font=("Consolas", 13, "bold"),
                          fill=COLOR["ink"] if ok else COLOR["closed"])
        y += 3 * (th + 8) + 4

        # 장치 상태 4 x 2
        items = [("난방", d.heater), ("냉방", d.cooler), ("환기", d.fan), ("가습", d.humidifier),
                 ("제습", d.dehumidifier), (f"조명{int(d.light * 100)}%" if d.light else "조명", d.light > 0),
                 ("급수", d.water_l > 0), ("비료", d.fertilizer_g > 0)]
        dw, dh = (self.W - 32 - 18) / 4, 26
        for k, (name, on) in enumerate(items):
            x1, y1 = 16 + (k % 4) * (dw + 6), y + (k // 4) * (dh + 6)
            c.create_rectangle(x1, y1, x1 + dw, y1 + dh, fill=COLOR["on"] if on else COLOR["off"], outline="")
            c.create_text(x1 + dw / 2, y1 + dh / 2, text=name, font=(FONT, 8, "bold"),
                          fill="#ffffff" if on else COLOR["muted"])
        y += 2 * (dh + 6) + 6

        # 동작 버튼
        bw = (self.W - 32 - 8) / 2
        for k, (text, action, fill) in enumerate([("수확 / 정리", app.harvest, COLOR["healthy"]),
                                                  ("갈아엎기", app.plow, COLOR["closed"])]):
            x1 = 16 + k * (bw + 8)
            c.create_rectangle(x1, y, x1 + bw, y + 40, fill=fill, outline="")
            c.create_text(x1 + bw / 2, y + 20, text=text, font=(FONT, 10, "bold"), fill="#ffffff")
            self.button((x1, y, x1 + bw, y + 40), action)

    def draw_alerts(self):
        c = self.canvas
        warns = [text for _, text, warn in self.app.entries if warn]
        y = self.header("알림", f"경고 {len(warns)}건 · 최근 것부터")
        bottom = self.H - self.NAV - 8
        if not warns:
            c.create_text(self.W / 2, y + 60, text="아직 알림이 없습니다.", font=(FONT, 10), fill=COLOR["muted"])
            return
        for text in reversed(warns):
            item = c.create_text(28, y + 10, anchor="nw", text=text, width=self.W - 60,
                                 font=(FONT, 9), fill=COLOR["ink"])
            _, _, _, ty2 = c.bbox(item)
            if ty2 + 10 > bottom:
                c.delete(item)
                break
            box = c.create_rectangle(16, y, self.W - 16, ty2 + 10, fill=COLOR["card"], outline=COLOR["line"])
            c.create_rectangle(16, y, 20, ty2 + 10, fill=COLOR["closed"], outline="")
            c.tag_lower(box)
            y = ty2 + 18
