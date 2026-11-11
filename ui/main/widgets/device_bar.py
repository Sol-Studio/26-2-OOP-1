"""장치 켜짐 표시 줄 (난방·냉방·환기·가습·제습·조명·급수·비료)"""
from ui.theme import COLOR, FONT


def draw_devices(c, d, x, y, small=False):
    items = [("난방", d.heater), ("냉방", d.cooler), ("환기", d.fan), ("가습", d.humidifier),
             ("제습", d.dehumidifier), (f"조명{int(d.light * 100)}%" if d.light else "조명", d.light > 0),
             ("급수", d.water_l > 0), ("비료", d.fertilizer_g > 0)]
    w = 19 if small else 62
    for k, (name, on) in enumerate(items):
        xx = x + k * (w + 1)
        if small:
            c.create_rectangle(xx, y - 7, xx + w - 2, y + 7, fill=COLOR["on"] if on else COLOR["off"], outline="")
            c.create_text(xx + w / 2 - 1, y, text=name[0], font=(FONT, 7, "bold"),
                          fill="#ffffff" if on else COLOR["muted"])
        else:
            c.create_rectangle(xx, y - 11, xx + w - 4, y + 11, fill=COLOR["on"] if on else COLOR["off"], outline="")
            c.create_text(xx + (w - 4) / 2, y, text=name, font=(FONT, 8, "bold"),
                          fill="#ffffff" if on else COLOR["muted"])
