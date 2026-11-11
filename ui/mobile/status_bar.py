"""맨 위 상태 표시줄: 시각과 앱 이름"""
from ui.theme import FONT


def draw_status_bar(win):
    c, f = win.canvas, win.app.farm
    c.create_rectangle(0, 0, win.W, win.BAR, fill="#18201b", outline="")
    c.create_text(16, win.BAR / 2, anchor="w", font=(FONT, 9, "bold"), fill="#ffffff",
                  text=f"{int(f.hour):02d}:{int(f.hour % 1 * 60):02d}")
    c.create_text(win.W - 16, win.BAR / 2, anchor="e", font=(FONT, 8), fill="#d6e6d9", text="EverGrow")
