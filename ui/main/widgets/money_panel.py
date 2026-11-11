"""선택한 구역의 이번 재배 비용·예상 수익"""
from core.economics import section_money, won
from ui.theme import COLOR, FONT


def draw_money(c, farm, s, x, y, w, h):
    price = farm.market.price(s.env_state.plant_profile.species)
    items, cost, expected = section_money(s, price)
    c.create_rectangle(x, y, x + w, y + h, fill=COLOR["card"], outline=COLOR["line"])
    c.create_text(x + 10, y + 14, anchor="w", text="이번 재배 비용", font=(FONT, 9, "bold"), fill=COLOR["ink"])
    for k, (name, v) in enumerate(items):
        c.create_text(x + 10, y + 34 + k * 15, anchor="w", text=name, font=(FONT, 8), fill=COLOR["muted"])
        c.create_text(x + w - 10, y + 34 + k * 15, anchor="e", text=won(v), font=("Consolas", 9), fill=COLOR["ink"])
    c.create_line(x + 10, y + 94, x + w - 10, y + 94, fill=COLOR["line"])
    c.create_text(x + 10, y + 106, anchor="w", text="합계", font=(FONT, 8), fill=COLOR["muted"])
    c.create_text(x + w - 10, y + 106, anchor="e", text=won(cost), font=("Consolas", 9, "bold"), fill=COLOR["ink"])
    if expected is None:
        c.create_text(x + 10, y + 128, anchor="w", text="예상 수익 없음", font=(FONT, 8), fill=COLOR["muted"])
    else:
        net = expected - cost
        c.create_text(x + 10, y + 124, anchor="w", text=f"예상 수익 {won(expected)}", font=(FONT, 8), fill=COLOR["muted"])
        c.create_text(x + 10, y + 140, anchor="w", font=(FONT, 8), fill=COLOR["muted"],
                      text=f"현재 시세 {price:,.0f}원/kg")
        c.create_text(x + w - 10, y + 124, anchor="e", text=f"순이익 {net:+,.0f}원",
                      font=(FONT, 9, "bold"), fill=COLOR["healthy"] if net >= 0 else COLOR["closed"])
