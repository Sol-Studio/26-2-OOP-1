"""구역 탭: 생육 카드, 비용, 환경 값, 장치 상태, 수확·갈아엎기 버튼"""
from ui.mobile.tabs.zone_cost import draw_cost
from ui.theme import CHARTS, COLOR, FONT


def draw_zone(win):
    c, app = win.canvas, win.app
    s = app.farm.sections[app.selected]
    ps, e, p, d = s.plant_state, s.env_state, s.env_state.plant_profile, s.devices
    label, col = app.status(s)
    y = win.header(f"‹ {s.label}", "")
    win.button((0, win.BAR, 200, y - 28), lambda: win.go("home"))
    c.create_text(16, y - 20, anchor="w", text=label, font=(FONT, 9, "bold"), fill=col)

    # 생육 카드
    c.create_rectangle(16, y, win.W - 16, y + 84, fill=COLOR["card"], outline=COLOR["line"])
    if ps:
        left = ps.hours_to_harvest()
        info = ("고사" if not ps.alive else "수확 가능" if ps.ready
                else "계산 중" if left is None else f"수확까지 {left / 24:.1f}일")
        c.create_text(28, y + 16, anchor="w", text=p.stage(ps.growth), font=(FONT, 11, "bold"), fill=COLOR["ink"])
        c.create_text(win.W - 28, y + 16, anchor="e", text=info, font=(FONT, 9), fill=COLOR["muted"])
        for j, (name, v, bc) in enumerate([("생장", ps.growth, COLOR["ready"] if ps.ready else COLOR["plot"]),
                                           ("건강", ps.health, col)]):
            yy = y + 42 + j * 22
            c.create_text(28, yy, anchor="w", text=name, font=(FONT, 8), fill=COLOR["muted"])
            win.bar(66, win.W - 64, yy - 3, v, bc)
            c.create_text(win.W - 28, yy, anchor="e", text=f"{v:.0f}%", font=("Consolas", 9), fill=COLOR["ink"])
    else:
        c.create_text(win.W / 2, y + 42, text="빈 구역입니다.\n관리 패널에서 작물을 심으세요.",
                      font=(FONT, 9), fill=COLOR["muted"], justify="center")
    y = draw_cost(win, s, y + 90)

    # 환경 값 2열 x 3줄 (적정 범위를 벗어나면 빨간색)
    tw, th = (win.W - 32 - 8) / 2, 44
    for k, (title, get, (_, hi), band, unit) in enumerate(CHARTS):
        x1, y1 = 16 + (k % 2) * (tw + 8), y + (k // 2) * (th + 8)
        v, (b_lo, b_hi) = get(s), band(p)
        ok = b_lo <= v <= b_hi
        val = f"{v:,.0f}" if hi >= 1000 else (f"{v:.2f}" if hi < 10 else f"{v:.1f}")
        c.create_rectangle(x1, y1, x1 + tw, y1 + th, fill=COLOR["card"], outline=COLOR["line"])
        c.create_text(x1 + 10, y1 + 12, anchor="w", text=title, font=(FONT, 8), fill=COLOR["muted"])
        c.create_text(x1 + tw - 10, y1 + 12, anchor="e", text=unit, font=(FONT, 7), fill=COLOR["muted"])
        c.create_text(x1 + 10, y1 + 30, anchor="w", text=val, font=("Consolas", 13, "bold"),
                      fill=COLOR["ink"] if ok else COLOR["closed"])
    y += 3 * (th + 8) + 4

    # 장치 상태 4 x 2
    items = [("난방", d.heater), ("냉방", d.cooler), ("환기", d.fan), ("가습", d.humidifier),
             ("제습", d.dehumidifier), (f"조명{int(d.light * 100)}%" if d.light else "조명", d.light > 0),
             ("급수", d.water_l > 0), ("비료", d.fertilizer_g > 0)]
    dw, dh = (win.W - 32 - 18) / 4, 26
    for k, (name, on) in enumerate(items):
        x1, y1 = 16 + (k % 4) * (dw + 6), y + (k // 4) * (dh + 6)
        c.create_rectangle(x1, y1, x1 + dw, y1 + dh, fill=COLOR["on"] if on else COLOR["off"], outline="")
        c.create_text(x1 + dw / 2, y1 + dh / 2, text=name, font=(FONT, 8, "bold"),
                      fill="#ffffff" if on else COLOR["muted"])
    y += 2 * (dh + 6) + 6

    # 동작 버튼
    bw = (win.W - 32 - 8) / 2
    for k, (text, action, fill) in enumerate([("수확 / 정리", app.harvest, COLOR["healthy"]),
                                              ("갈아엎기", app.plow, COLOR["closed"])]):
        x1 = 16 + k * (bw + 8)
        c.create_rectangle(x1, y, x1 + bw, y + 40, fill=fill, outline="")
        c.create_text(x1 + bw / 2, y + 20, text=text, font=(FONT, 10, "bold"), fill="#ffffff")
        win.button((x1, y, x1 + bw, y + 40), action)
