"""맨 위 줄: 날짜·시각, 바깥 날씨, 하루 진행 막대"""
from ui.theme import COLOR, FONT


def draw_header(c, farm):
    f, w = farm, farm.weather
    h = f.hour
    c.create_text(16, 20, anchor="w", font=(FONT, 15, "bold"), fill=COLOR["ink"],
                  text=f"Day {f.day}  {int(h):02d}:{int(h % 1 * 60):02d}")
    sky = "밤" if w.sunlight <= 0 else ("흐림" if w.cloud > 0.5 else "맑음")
    c.create_text(170, 20, anchor="w", font=(FONT, 10), fill=COLOR["muted"],
                  text=f"바깥  {w.temperature:.1f}°C · 습도 {w.humidity:.0f}% · 햇빛 {w.sunlight:,.0f}lux · {sky}")
    # 하루 진행 막대 (낮/밤)
    x0, x1, y = 16, 560, 44
    c.create_rectangle(x0, y, x1, y + 6, fill=COLOR["night"], outline="")
    c.create_rectangle(x0 + (x1 - x0) * 6 / 24, y, x0 + (x1 - x0) * 18 / 24, y + 6, fill="#f5dc8a", outline="")
    cx = x0 + (x1 - x0) * h / 24
    c.create_oval(cx - 5, y - 2, cx + 5, y + 8, fill=COLOR["ink"], outline="")
