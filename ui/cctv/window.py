import tkinter as tk

from core.catalog import ZONES
from ui.theme import COLOR, FONT
from ui.shared.cctv_view import draw_cctv


class CctvWindow(tk.Toplevel):
    """구역 6곳의 CCTV를 한 화면에 모아 보는 창. 화면을 누르면 그 구역이 선택된다."""
    CW, CH, GAP = 300, 210, 10
    COLS = 3

    def __init__(self, app):
        super().__init__(app.root, bg=COLOR["bg"], padx=10, pady=10)
        self.app = app
        self.title("에버그로우 - CCTV")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.withdraw)   # 닫아도 관리 패널에서 다시 열 수 있게 숨기기만
        rows = -(-len(ZONES) // self.COLS)
        self.canvas = tk.Canvas(self, width=self.COLS * (self.CW + self.GAP) - self.GAP,
                                height=rows * (self.CH + 24 + self.GAP), bg=COLOR["bg"], highlightthickness=0)
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.on_click)
        self.boxes = []
        self.withdraw()

    def on_click(self, e):
        for i, (x1, y1, x2, y2) in enumerate(self.boxes):
            if x1 <= e.x <= x2 and y1 <= e.y <= y2:
                self.app.select(i)

    def refresh(self):
        if self.state() == "withdrawn":
            return
        c, app = self.canvas, self.app
        c.delete("all")
        self.boxes = []
        for i, s in enumerate(app.farm.sections):
            x1 = (i % self.COLS) * (self.CW + self.GAP)
            y1 = (i // self.COLS) * (self.CH + 24 + self.GAP)
            label, col = app.status(s)
            c.create_text(x1 + 2, y1 + 10, anchor="w", text=s.label, font=(FONT, 10, "bold"), fill=COLOR["ink"])
            c.create_text(x1 + self.CW - 2, y1 + 10, anchor="e", text=label, font=(FONT, 9, "bold"), fill=col)
            draw_cctv(c, x1, y1 + 22, self.CW, self.CH, s, app.farm, i + 1)
            if i == app.selected:
                c.create_rectangle(x1, y1 + 22, x1 + self.CW, y1 + 22 + self.CH, outline=COLOR["plot"], width=3)
            self.boxes.append((x1, y1, x1 + self.CW, y1 + 22 + self.CH))
