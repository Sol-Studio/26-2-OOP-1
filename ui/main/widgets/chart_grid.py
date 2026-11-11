"""최근 24시간 그래프 6개: 적정 범위 띠, 밤 음영, 현재 값"""
from ui.theme import CHARTS, COLOR, FONT, HISTORY

CHART_W, CHART_GAP = 290, 18


def draw_charts(c, p, hist, nights, ox, y0=156):
    """p: 작물 정보, hist: 단계별 값 목록, nights: 단계별 밤 여부"""
    gh, gy = 110, 22
    gh, gy = 110, 22
    for k, (title, _, (lo, hi), band, unit) in enumerate(CHARTS):
        col, row = k % 2, k // 2
        x1 = ox + col * (CHART_W + CHART_GAP)
        y1 = y0 + row * (gh + gy)
        x2, y2 = x1 + CHART_W, y1 + gh
        top, bot = y1 + 18, y2 - 4
        ymap = lambda v: bot - (min(max(v, lo), hi) - lo) / (hi - lo) * (bot - top)
        xstep = CHART_W / (HISTORY - 1)

        c.create_rectangle(x1, top, x2, bot, fill=COLOR["card"], outline=COLOR["line"])
        # 밤 구간 음영
        for i, night in enumerate(nights):
            if night:
                c.create_rectangle(x1 + i * xstep, top + 1, x1 + (i + 1) * xstep, bot - 1,
                                   fill=COLOR["night"], outline="")
        b_lo, b_hi = band(p)
        c.create_rectangle(x1 + 1, ymap(b_hi), x2 - 1, ymap(b_lo), fill=COLOR["band"], outline="")
        for v in (lo, hi):
            c.create_text(x1 - 3, ymap(v), anchor="e", text=f"{v:g}", font=("Consolas", 7), fill=COLOR["muted"])

        pts = [(x1 + i * xstep, ymap(h[k])) for i, h in enumerate(hist)]
        if len(pts) > 1:
            c.create_line(*[v for pt in pts for v in pt], fill=COLOR["plot"], width=2)
        cur = hist[-1][k]
        ok = b_lo <= cur <= b_hi
        if pts:
            c.create_oval(pts[-1][0] - 3, pts[-1][1] - 3, pts[-1][0] + 3, pts[-1][1] + 3,
                          fill=COLOR["plot"] if ok else COLOR["closed"], outline="")
        c.create_text(x1, y1 + 6, anchor="w", text=title, font=(FONT, 9, "bold"), fill=COLOR["ink"])
        val = f"{cur:,.0f}" if hi >= 1000 else (f"{cur:.2f}" if hi < 10 else f"{cur:.1f}")
        c.create_text(x2, y1 + 6, anchor="e", text=f"{val} {unit}", font=("Consolas", 9, "bold"),
                      fill=COLOR["ink"] if ok else COLOR["closed"])
