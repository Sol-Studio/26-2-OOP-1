import tkinter as tk

from ui.mobile.nav_bar import draw_nav
from ui.mobile.status_bar import draw_status_bar
from ui.mobile.tabs import DRAW, TABS
from ui.theme import COLOR, FONT


class MobileWindow(tk.Toplevel):
    """농장주가 휴대폰으로 보는 앱 화면(9:16). 홈 / CCTV / 구역 상세 / 알림 네 탭을 오간다."""
    W, H = 360, 640
    BAR, NAV = 26, 56          # 위 상태 표시줄, 아래 탭 바 높이
    TABS = TABS

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
        draw_status_bar(self)
        DRAW[self.tab](self)
        draw_nav(self)

    def header(self, title, sub):
        c, y = self.canvas, self.BAR + 14
        c.create_text(16, y + 10, anchor="w", text=title, font=(FONT, 16, "bold"), fill=COLOR["ink"])
        c.create_text(16, y + 36, anchor="w", text=sub, font=(FONT, 9), fill=COLOR["muted"])
        return y + 56

    def bar(self, x1, x2, y, value, color, h=6):
        self.canvas.create_rectangle(x1, y, x2, y + h, fill=COLOR["off"], outline="")
        self.canvas.create_rectangle(x1, y, x1 + (x2 - x1) * value / 100, y + h, fill=color, outline="")
