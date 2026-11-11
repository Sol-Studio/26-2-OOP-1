"""알림 탭: 경고 로그를 최근 순으로"""
from ui.theme import COLOR, FONT


def draw_alerts(win):
    c = win.canvas
    warns = [text for _, text, warn in win.app.entries if warn]
    y = win.header("알림", f"경고 {len(warns)}건 · 최근 것부터")
    bottom = win.H - win.NAV - 8
    if not warns:
        c.create_text(win.W / 2, y + 60, text="아직 알림이 없습니다.", font=(FONT, 10), fill=COLOR["muted"])
        return
    for text in reversed(warns):
        item = c.create_text(28, y + 10, anchor="nw", text=text, width=win.W - 60,
                             font=(FONT, 9), fill=COLOR["ink"])
        _, _, _, ty2 = c.bbox(item)
        if ty2 + 10 > bottom:
            c.delete(item)
            break
        box = c.create_rectangle(16, y, win.W - 16, ty2 + 10, fill=COLOR["card"], outline=COLOR["line"])
        c.create_rectangle(16, y, 20, ty2 + 10, fill=COLOR["closed"], outline="")
        c.tag_lower(box)
        y = ty2 + 18
