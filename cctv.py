"""구역별 CCTV 화면. 실제 영상이 아니라 구역 상태를 그려서 보여 준다."""
from common import FONT

FRUIT_COLOR = {"토마토": "#d63a2f", "딸기": "#e0405a", "파프리카": "#e8a91c", "오이": "#4f9a3a"}


def _mix(a, b, t):
    """색 a에서 b로 t(0~1)만큼 섞는다."""
    t = min(max(t, 0), 1)
    pa = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    pb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(pa, pb))


def draw_cctv(c, x, y, w, h, section, farm, cam, compact=False):
    """canvas c의 (x, y, w, h) 칸에 구역 하나의 CCTV 화면을 그린다. compact면 글자를 줄인다."""
    ps, e, d = section.plant_state, section.env_state, section.devices
    species = e.plant_profile.species
    day = 6 <= farm.hour < 18
    lit = d.light > 0

    # 온실 안 벽과 바닥 (밤에는 어둡고, 조명이 켜져 있으면 따뜻한 빛이 돈다)
    wall = "#d4e4d6" if day else "#16231c"
    if lit:
        wall = _mix(wall, "#f2e2a0", 0.35 if day else 0.3)
    soil_y = y + h * 0.62
    c.create_rectangle(x, y, x + w, soil_y, fill=wall, outline="")
    for k in range(1, 6):                         # 온실 지붕 뼈대
        gx = x + w * k / 6
        c.create_line(gx, y, gx - w * 0.04, soil_y, fill=_mix(wall, "#000000", 0.18))
    soil = "#8a6a4a" if day else "#3a2d20"
    c.create_rectangle(x, soil_y, x + w, y + h, fill=soil, outline="")
    for k in range(4):                            # 이랑
        yy = soil_y + (y + h - soil_y) * (k + 0.5) / 4
        c.create_line(x, yy, x + w, yy, fill=_mix(soil, "#000000", 0.25))
    if lit:
        c.create_rectangle(x + w * 0.1, y + 2, x + w * 0.9, y + 6, fill="#fff3b0", outline="")
        c.create_polygon(x + w * 0.1, y + 6, x + w * 0.9, y + 6, x + w * 0.98, soil_y, x + w * 0.02, soil_y,
                         fill="#fff3b0", outline="", stipple="gray12")

    # 작물
    n = 5
    if ps is None:
        c.create_text(x + w / 2, soil_y - h * 0.12, text="빈 구역", font=(FONT, 8 if compact else 10),
                      fill="#6b7a70" if day else "#9fb0a5")
    else:
        g = ps.growth
        top_h = (soil_y - y) * (0.12 + 0.62 * g / 100)
        leaf = _mix("#2f7d4a", "#c8b64a", (100 - ps.health) / 100 * 1.4) if ps.alive else "#8b7d5a"
        if not day and not lit:
            leaf = _mix(leaf, "#000000", 0.45)
        base_y = soil_y + (y + h - soil_y) * 0.3
        for i in range(n):
            px = x + w * (i + 0.5) / n
            ph = top_h * (0.9 + 0.1 * ((i * 7) % 3))          # 포기마다 키를 조금씩 다르게
            if not ps.alive:                                  # 고사: 꺾인 줄기
                c.create_line(px, base_y, px + w * 0.03, base_y - ph * 0.5, fill=leaf, width=2)
                c.create_line(px + w * 0.03, base_y - ph * 0.5, px + w * 0.06, base_y - ph * 0.4, fill=leaf, width=2)
                continue
            c.create_line(px, base_y, px, base_y - ph, fill=_mix(leaf, "#000000", 0.25), width=2)
            r = max(3, ph * 0.28)
            if g < 10:                                        # 발아: 떡잎 두 장
                c.create_oval(px - r, base_y - ph - r * 0.4, px, base_y - ph + r * 0.4, fill=leaf, outline="")
                c.create_oval(px, base_y - ph - r * 0.4, px + r, base_y - ph + r * 0.4, fill=leaf, outline="")
            else:
                for dx, dy, k in ((-0.7, 0.55, 1.0), (0.7, 0.55, 1.0), (0, 0.15, 1.15), (-0.4, 0.95, 0.8), (0.4, 0.95, 0.8)):
                    c.create_oval(px + dx * r - r * k * 0.8, base_y - ph * dy - r * k * 0.6,
                                  px + dx * r + r * k * 0.8, base_y - ph * dy + r * k * 0.6, fill=leaf, outline="")
            if species in FRUIT_COLOR and g >= 55:            # 개화 이후 열매
                fr = max(2, r * 0.35)
                for dx, dy in ((-0.9, 0.35), (0.8, 0.5)):
                    fx, fy = px + dx * r, base_y - ph * dy
                    c.create_oval(fx - fr, fy - fr, fx + fr, fy + fr,
                                  fill=FRUIT_COLOR[species] if g >= 75 else "#9bc47a", outline="")
            if ps.pests:                                      # 병충해: 잎 위의 벌레
                for dx, dy in ((-0.6, 0.6), (0.5, 0.9), (0.1, 0.25)):
                    bx, by = px + dx * r, base_y - ph * dy
                    c.create_oval(bx - 1.8, by - 1.8, bx + 1.8, by + 1.8, fill="#2b1d12", outline="")

    # 구역 격리 (차폐막)
    if section.is_closed:
        c.create_rectangle(x, y, x + w, y + h, fill="#c0582a", outline="", stipple="gray25")
        c.create_text(x + w / 2, y + h / 2, text="격리·방제 중", font=(FONT, 9 if compact else 12, "bold"), fill="#ffffff")

    # 급수·살포 표시
    if d.water_l > 0:
        for k in range(6):
            wx = x + w * (k + 0.5) / 6
            c.create_line(wx, soil_y - h * 0.18, wx, soil_y, fill="#4aa3df", dash=(2, 3))

    # CCTV 겉모습: 테두리, 녹화 표시, 카메라 이름, 시각
    c.create_rectangle(x, y, x + w, y + h, outline="#111814", width=2)
    fs = 7 if compact else 8
    blink = int(farm.hours * 6) % 2 == 0
    c.create_oval(x + 6, y + 6, x + 12, y + 12, fill="#d6322b" if blink else wall, outline="")
    c.create_text(x + 16, y + 9, anchor="w", text="REC", font=("Consolas", fs, "bold"), fill="#d6322b")
    tag = f"CAM {cam:02d}"
    c.create_text(x + w - 6, y + 9, anchor="e", text=tag, font=("Consolas", fs, "bold"),
                  fill="#1d2620" if day else "#e8efe9")
    stamp = f"Day{farm.day} {int(farm.hour):02d}:{int(farm.hour % 1 * 60):02d}"
    c.create_text(x + 6, y + h - 8, anchor="w", text=stamp, font=("Consolas", fs, "bold"), fill="#f2f2f2")
    if not compact:
        c.create_text(x + w - 6, y + h - 8, anchor="e", text=section.label, font=(FONT, fs, "bold"), fill="#f2f2f2")
