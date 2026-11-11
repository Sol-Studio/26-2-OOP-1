"""구역 카드 6장: 상태, 적정 범위 대비 현재 값, 건강·생장 막대, 장치 표시"""
from ui.main.widgets.device_bar import draw_devices
from ui.theme import COLOR, FONT


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
        fill = ("#fbe6da" if s.is_closed else COLOR["empty"] if not ps
                else "#eeeeee" if not ps.alive else COLOR["card"])
        sel = i == selected
        c.create_rectangle(x1, y1, x2, y2, fill=fill, outline=COLOR["plot"] if sel else COLOR["line"],
                           width=3 if sel else 1)
        c.create_text(x1 + 10, y1 + 16, anchor="w", text=s.label, font=(FONT, 10, "bold"), fill=COLOR["ink"])
        c.create_text(x2 - 10, y1 + 16, anchor="e", text=label, font=(FONT, 8, "bold"), fill=color)

        e, p = s.env_state, s.env_state.plant_profile
        rows = [("온도", e.temperature, p.temperature_range, f"{e.temperature:.1f}°"),
                ("습도", e.humidity, p.humidity_range, f"{e.humidity:.0f}%"),
                ("토양", e.soil_humidity, p.soil_humidity_range, f"{e.soil_humidity:.0f}%"),
                ("EC", e.nutrient, p.nutrient_range, f"{e.nutrient:.2f}")]
        for j, (name, v, (lo, hi), txt) in enumerate(rows):
            yy = y1 + 38 + j * 17
            ok = lo <= v <= hi
            c.create_text(x1 + 10, yy, anchor="w", text=name, font=(FONT, 8), fill=COLOR["muted"])
            c.create_text(x2 - 10, yy, anchor="e", text=txt, font=("Consolas", 9),
                          fill=COLOR["ink"] if ok else COLOR["closed"])
            c.create_text(x1 + 50, yy, anchor="w", text=f"{lo:g}~{hi:g}", font=("Consolas", 8), fill=COLOR["muted"])

        if not ps:
            c.create_text(x1 + cw / 2, y1 + 120, text="비어 있음 · 작물을 골라 심기",
                          font=(FONT, 8), fill=COLOR["muted"])
        else:
            grow_col = COLOR["ready"] if ps.ready else COLOR["plot"]
            bars = [("건강", ps.health, color), (p.stage(ps.growth), ps.growth, grow_col)]
            for j, (name, v, col_) in enumerate(bars):
                yy = y1 + 112 + j * 16
                c.create_text(x1 + 10, yy, anchor="w", text=name, font=(FONT, 8), fill=COLOR["muted"])
                c.create_rectangle(x1 + 64, yy - 3, x2 - 38, yy + 3, fill=COLOR["off"], outline="")
                c.create_rectangle(x1 + 64, yy - 3, x1 + 64 + (cw - 102) * v / 100, yy + 3, fill=col_, outline="")
                c.create_text(x2 - 10, yy, anchor="e", text=f"{v:.0f}", font=("Consolas", 8), fill=COLOR["ink"])
        draw_devices(c, s.devices, x1 + 10, y1 + 152, small=True)

    c.create_text(16, oy + 2 * (ch + gap) + 4, anchor="nw", font=(FONT, 9), fill=COLOR["muted"],
                  text="카드를 클릭하면 오른쪽에 그 구역의 생육 단계와 24시간 그래프가 나옵니다.\n"
                       "빨간 값은 적정 범위를 벗어난 값입니다.")
    return boxes
