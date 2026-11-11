"""구역 탭의 재배 비용·예상 수익 카드"""
from core.economics import section_money, won
from ui.theme import COLOR, FONT


def draw_cost(win, s, y):
    """구역 상세의 재배 비용·예상 수익 카드. 카드 아래 y를 돌려준다."""
    c = win.canvas
    items, cost, expected = section_money(s, win.app.farm.market.price(s.env_state.plant_profile.species))
    h = 78
    c.create_rectangle(16, y, win.W - 16, y + h, fill=COLOR["card"], outline=COLOR["line"])
    c.create_text(28, y + 14, anchor="w", text="이번 재배 비용", font=(FONT, 8), fill=COLOR["muted"])
    c.create_text(28, y + 32, anchor="w", text=won(cost), font=(FONT, 11, "bold"), fill=COLOR["ink"])
    if expected is None:
        c.create_text(win.W - 28, y + 24, anchor="e", text="예상 수익 없음", font=(FONT, 9), fill=COLOR["muted"])
    else:
        c.create_text(win.W - 28, y + 14, anchor="e", text="예상 수익 · 순이익", font=(FONT, 8), fill=COLOR["muted"])
        net = expected - cost
        c.create_text(win.W - 28, y + 32, anchor="e", text=f"{won(expected)} · {net:+,.0f}원",
                      font=(FONT, 9, "bold"), fill=COLOR["healthy"] if net >= 0 else COLOR["closed"])
    cw = (win.W - 56) / 4
    for k, (name, v) in enumerate(items):
        x1 = 28 + k * cw
        c.create_text(x1, y + 52, anchor="w", text=name, font=(FONT, 8), fill=COLOR["muted"])
        c.create_text(x1, y + 66, anchor="w", text=f"{v:,.0f}", font=("Consolas", 9), fill=COLOR["ink"])
    return y + h + 8
