"""수확 기록 표와 누적 매출·비용·순이익"""
from core.economics import totals, won
from ui.theme import COLOR, FONT


def draw_harvests(c, farm):
    log = farm.harvests
    x1, x2, y = 16, 560, 498
    total = sum(h[3] for h in log)
    cost, rev, profit = totals(farm.cycles)
    c.create_text(x1, y, anchor="w", text="수확 기록", font=(FONT, 11, "bold"), fill=COLOR["ink"])
    c.create_text(x2, y, anchor="e", font=(FONT, 9), fill=COLOR["muted"],
                  text=f"총 {len(log)}회 · {total:.1f}kg · 매출 {won(rev)} · 비용 {won(cost)} · 순이익 {profit:+,.0f}원")
    c.create_line(x1, y + 14, x2, y + 14, fill=COLOR["line"])
    if not log:
        c.create_text(x1, y + 32, anchor="w", font=(FONT, 9), fill=COLOR["muted"],
                      text="아직 수확한 작물이 없습니다. 카드가 '수확 가능'이 되면 수확하세요.")
        return
    cols = [(x1, "w", "일차"), (x1 + 55, "w", "구역"), (x1 + 115, "w", "작물"),
            (x1 + 235, "e", "수확량"), (x1 + 325, "e", "수확 시세"), (x1 + 395, "e", "품질")]
    for x, anchor, text in cols:
        c.create_text(x, y + 28, anchor=anchor, text=text, font=(FONT, 8, "bold"), fill=COLOR["muted"])
    for k, (day, zone, crop, kg, quality, price) in enumerate(reversed(log[-10:])):
        yy = y + 46 + k * 18
        row = [f"Day {day}", zone, crop, f"{kg:.1f} kg", f"{price:,.0f}원", f"{quality:.0f}%"]
        for (x, anchor, _), text in zip(cols, row):
            c.create_text(x, yy, anchor=anchor, text=text, font=(FONT, 9), fill=COLOR["ink"])
        c.create_rectangle(x1 + 410, yy - 3, x1 + 410 + 1.2 * quality, yy + 3, outline="",
                           fill=COLOR["healthy"] if quality >= 70 else COLOR["closed"])
