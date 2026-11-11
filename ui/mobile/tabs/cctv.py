"""CCTV 탭: 선택한 구역을 크게, 나머지는 작게"""
from ui.shared.cctv_view import draw_cctv as draw_camera
from ui.theme import COLOR, FONT


def draw_cctv(win):
    c, app = win.canvas, win.app
    f = app.farm
    y = win.header("CCTV", "구역을 누르면 크게 봅니다")
    s = f.sections[app.selected]
    label, col = app.status(s)
    big_h = 196
    draw_camera(c, 16, y, win.W - 32, big_h, s, f, app.selected + 1)
    c.create_text(18, y + big_h + 14, anchor="w", text=s.label, font=(FONT, 10, "bold"), fill=COLOR["ink"])
    c.create_text(win.W - 18, y + big_h + 14, anchor="e", text=f"{label}  ›", font=(FONT, 9, "bold"), fill=col)
    win.button((16, y + big_h, win.W - 16, y + big_h + 28), lambda: win.go("zone"))
    y += big_h + 36
    tw, th, gap = (win.W - 32 - 12) / 3, 78, 6
    for i, sec in enumerate(f.sections):
        x1, y1 = 16 + (i % 3) * (tw + 6), y + (i // 3) * (th + gap)
        draw_camera(c, x1, y1, tw, th, sec, f, i + 1, compact=True)
        if i == app.selected:
            c.create_rectangle(x1, y1, x1 + tw, y1 + th, outline=COLOR["plot"], width=3)
        win.button((x1, y1, x1 + tw, y1 + th), lambda i=i: win.app.select(i))
