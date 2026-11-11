"""홈 탭: 요약 칩, 정산 요약, 구역 목록"""
from core.economics import totals, won
from ui.theme import COLOR, FONT


def draw_home(win):
    c, f, w = win.canvas, win.app.farm, win.app.farm.weather
    sky = "밤" if w.sunlight <= 0 else ("흐림" if w.cloud > 0.5 else "맑음")
    y = win.header("우리 농장", f"Day {f.day} · 바깥 {w.temperature:.1f}°C {sky} · 습도 {w.humidity:.0f}%")

    # 요약 칩: 수확 가능 / 주의 / 정상
    states = [win.app.status(s) for s in f.sections]
    ready = sum(1 for label, _ in states if label == "수확 가능")
    alert = sum(1 for _, col in states if col in (COLOR["closed"], COLOR["dead"]))
    chips = [("수확 가능", ready, COLOR["ready"]), ("주의", alert, COLOR["closed"]),
             ("전체 구역", len(states), COLOR["healthy"])]
    cw = (win.W - 32 - 16) / 3
    for k, (name, n, col) in enumerate(chips):
        x1 = 16 + k * (cw + 8)
        c.create_rectangle(x1, y, x1 + cw, y + 50, fill=COLOR["card"], outline=COLOR["line"])
        c.create_text(x1 + 10, y + 16, anchor="w", text=name, font=(FONT, 8), fill=COLOR["muted"])
        c.create_text(x1 + 10, y + 36, anchor="w", text=str(n), font=(FONT, 14, "bold"), fill=col)
    y += 58

    # 정산 요약: 끝난 재배(수확·갈아엎기·고사) 기준
    cost, rev, profit = totals(f.cycles)
    c.create_rectangle(16, y, win.W - 16, y + 44, fill=COLOR["card"], outline=COLOR["line"])
    for k, (name, v, col) in enumerate([("매출", rev, COLOR["ink"]), ("비용", cost, COLOR["ink"]),
                                        ("순이익", profit, COLOR["healthy"] if profit >= 0 else COLOR["closed"])]):
        x1 = 26 + k * (win.W - 32) / 3
        c.create_text(x1, y + 13, anchor="w", text=name, font=(FONT, 8), fill=COLOR["muted"])
        c.create_text(x1, y + 31, anchor="w", text=won(v), font=(FONT, 10, "bold"), fill=col)
    y += 52

    # 구역 목록: 누르면 구역 탭으로
    ch = (win.H - win.NAV - 10 - y) / len(f.sections)
    for i, s in enumerate(f.sections):
        y1, y2 = y + i * ch, y + (i + 1) * ch - 6
        label, col = win.app.status(s)
        ps, e = s.plant_state, s.env_state
        sel = i == win.app.selected
        c.create_rectangle(16, y1, win.W - 16, y2, fill=COLOR["card"],
                           outline=COLOR["plot"] if sel else COLOR["line"], width=2 if sel else 1)
        c.create_rectangle(16, y1, 21, y2, fill=col, outline="")
        c.create_text(32, y1 + 14, anchor="w", text=s.label, font=(FONT, 10, "bold"), fill=COLOR["ink"])
        c.create_text(win.W - 28, y1 + 14, anchor="e", text=f"{label}  ›", font=(FONT, 8, "bold"), fill=col)
        if ps:
            c.create_text(32, y2 - 12, anchor="w", font=("Consolas", 8), fill=COLOR["muted"],
                          text=f"{e.temperature:.1f}°  {e.humidity:.0f}%  {ps.growth:3.0f}%")
            win.bar(170, win.W - 28, y2 - 15, ps.growth, COLOR["ready"] if ps.ready else COLOR["plot"])
        else:
            c.create_text(32, y2 - 12, anchor="w", text="비어 있음", font=(FONT, 8), fill=COLOR["muted"])
        win.button((16, y1, win.W - 16, y2), lambda i=i: win.open_zone(i))
