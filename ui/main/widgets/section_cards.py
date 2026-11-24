"""구역 카드 6장: 상태, 작물과 생육 단계, 건강·생장 막대만 간단히 (환경 값·장치는 상세 패널에서)"""
from ui.theme import COLOR, FONT, health_color


def section_status(s):
    if not s.plant_state:
        return "파종 대기", COLOR["muted"]
    if not s.plant_state.alive:
        return "고사", COLOR["dead"]
    if s.is_closed:
        if s.control_failures:
            return f"방제 실패 {s.control_failures}회", COLOR["closed"]
        return "격리·방제 중", COLOR["closed"]
    if s.plant_state.ready:
        return "수확 가능", COLOR["ready"]
    return "정상", COLOR["healthy"]


def draw_section_cards(c, farm, selected):
    """카드를 그리고 클릭 판정용 상자 목록 [(x1, y1, x2, y2)]를 돌려준다."""
    cw, ch, gap, ox, oy = 176, 176, 10, 16, 66
    boxes = []
    for i, s in enumerate(farm.sections):
        col, row = i % 3, i // 3
        x1, y1 = ox + col * (cw + gap), oy + row * (ch + gap)
        x2, y2 = x1 + cw, y1 + ch
        boxes.append((x1, y1, x2, y2))
        label, color = section_status(s)
        ps = s.plant_state
        fill = (COLOR["closed_weak"] if s.is_closed else COLOR["empty"] if not ps
                else COLOR["dead_bg"] if not ps.alive else COLOR["card"])
        sel = i == selected
        c.create_rectangle(x1, y1, x2, y2, fill=fill, outline=COLOR["plot"] if sel else COLOR["line"],
                           width=3 if sel else 1)
        c.create_text(x1 + 10, y1 + 16, anchor="w", text=s.label, font=(FONT, 10, "bold"), fill=COLOR["ink"])
        c.create_text(x2 - 10, y1 + 16, anchor="e", text=label, font=(FONT, 8, "bold"), fill=color)

        if not ps:
            c.create_text(x1 + cw / 2, y1 + ch / 2 + 8, text="비어 있음\n작물을 골라 심기", justify="center",
                          font=(FONT, 9), fill=COLOR["muted"])
            continue
        p = s.env_state.plant_profile
        c.create_text(x1 + 10, y1 + 48, anchor="w", text="생육 단계", font=(FONT, 8), fill=COLOR["muted"])
        c.create_text(x1 + 10, y1 + 72, anchor="w", text=p.stage(ps.growth), font=(FONT, 13, "bold"), fill=COLOR["ink"])
        grow_col = COLOR["ready"] if ps.ready else COLOR["plot"]
        for j, (name, v, col_) in enumerate([("건강", ps.health, health_color(ps.health)), ("생장", ps.growth, grow_col)]):
            yy = y1 + 112 + j * 30
            c.create_text(x1 + 10, yy, anchor="w", text=name, font=(FONT, 9), fill=COLOR["muted"])
            c.create_rectangle(x1 + 46, yy - 4, x2 - 42, yy + 4, fill=COLOR["off"], outline="")
            c.create_rectangle(x1 + 46, yy - 4, x1 + 46 + (cw - 88) * v / 100, yy + 4, fill=col_, outline="")
            c.create_text(x2 - 10, yy, anchor="e", text=f"{v:.0f}%", font=("Consolas", 9), fill=COLOR["ink"])

    c.create_text(16, oy + 2 * (ch + gap) + 4, anchor="nw", font=(FONT, 9), fill=COLOR["muted"],
                  text="카드를 클릭하면 오른쪽에 그 구역의 환경 값, 장치 상태, 24시간 그래프가 나옵니다.")
    return boxes
