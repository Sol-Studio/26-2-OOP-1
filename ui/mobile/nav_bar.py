"""아래 탭 바: 탭 이동 버튼과 알림 개수 뱃지"""
from ui.theme import COLOR, FONT


def draw_nav(win):
    c, top = win.canvas, win.H - win.NAV
    c.create_rectangle(0, top, win.W, win.H, fill=COLOR["card"], outline="")
    c.create_line(0, top, win.W, top, fill=COLOR["line"])
    warns = sum(1 for _, _, warn in win.app.entries if warn)
    w = win.W / len(win.TABS)
    for k, (key, name) in enumerate(win.TABS):
        x1 = k * w
        on = key == win.tab
        if on:
            c.create_rectangle(x1 + w / 2 - 18, top + 6, x1 + w / 2 + 18, top + 9, fill=COLOR["healthy"], outline="")
        c.create_text(x1 + w / 2, top + win.NAV / 2 + 2, text=name, font=(FONT, 10, "bold" if on else "normal"),
                      fill=COLOR["healthy"] if on else COLOR["muted"])
        if key == "alerts" and warns:
            c.create_oval(x1 + w / 2 + 20, top + 12, x1 + w / 2 + 38, top + 28, fill=COLOR["closed"], outline="")
            c.create_text(x1 + w / 2 + 29, top + 20, text=str(min(warns, 99)), font=(FONT, 7, "bold"), fill="#ffffff")
        win.button((x1, top, x1 + w, win.H), lambda key=key: win.go(key))
