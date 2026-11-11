"""생육 단계 타임라인: 단계별 구간, 현재 생장도, 수확 예상"""
from ui.theme import COLOR, FONT


def draw_growth(c, s, ox, y, right):
    ps, p = s.plant_state, s.env_state.plant_profile
    x1, x2 = ox, right
    top, bot = y + 18, y + 32
    c.create_text(x1, y, anchor="w", text="생육 단계", font=(FONT, 10, "bold"), fill=COLOR["ink"])
    if not ps:
        c.create_rectangle(x1, top, x2, bot, fill=COLOR["off"], outline="")
        c.create_text(x1 + 70, y, anchor="w", font=(FONT, 9), fill=COLOR["muted"],
                      text="빈 구역 · 작물을 고르고 '심기'를 누르세요")
        return

    xmap = lambda g: x1 + (x2 - x1) * g / 100
    current = p.stage(ps.growth)
    fill = COLOR["dead"] if not ps.alive else COLOR["ready"] if ps.ready else COLOR["healthy"]
    c.create_rectangle(x1, top, x2, bot, fill=COLOR["off"], outline="")
    c.create_rectangle(x1, top, xmap(ps.growth), bot, fill=fill, outline="")
    stages = p.stages
    for k, (name, start) in enumerate(stages[:-1]):
        end = stages[k + 1][1]
        if k:
            c.create_line(xmap(start), top - 3, xmap(start), bot + 3, fill=COLOR["card"], width=2)
        c.create_text((xmap(start) + xmap(end)) / 2, bot + 10, text=name,
                      font=(FONT, 8, "bold" if name == current else "normal"),
                      fill=COLOR["ink"] if name == current else COLOR["muted"])
    c.create_text(x2, bot + 10, anchor="e", text=stages[-1][0],
                  font=(FONT, 8, "bold" if ps.ready else "normal"),
                  fill=COLOR["ready"] if ps.ready else COLOR["muted"])
    mx = xmap(ps.growth)
    c.create_polygon(mx - 5, top - 9, mx + 5, top - 9, mx, top - 2, fill=COLOR["ink"], outline="")

    # 요약 줄
    if not ps.alive:
        info, col = "고사 · '수확 / 정리'로 비우세요", COLOR["dead"]
    elif ps.ready:
        info, col = "수확 가능 · 늦으면 상합니다", COLOR["ready"]
    else:
        left = ps.hours_to_harvest()
        info = "수확까지 계산 중" if left is None else f"수확까지 약 {left / 24:.1f}일"
        col = COLOR["ink"]
    c.create_text(x1 + 70, y, anchor="w", font=(FONT, 9), fill=col,
                  text=f"{current} {ps.growth:.0f}% · {info}")
    c.create_text(x2, y, anchor="e", font=(FONT, 9), fill=COLOR["muted"],
                  text=f"파종 후 {ps.age_hours / 24:.1f}일 · 평균 건강 {ps.avg_health:.0f} · "
                       f"예상 수확량 {p.yield_kg * ps.avg_health / 100:.1f}kg")
