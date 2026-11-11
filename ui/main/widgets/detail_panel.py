"""오른쪽 상세 영역: 선택한 구역의 장치, 생육 단계, 24시간 그래프, CCTV, 비용"""
from ui.shared.cctv_view import draw_cctv
from ui.main.widgets.chart_grid import CHART_GAP, CHART_W, draw_charts
from ui.main.widgets.device_bar import draw_devices
from ui.main.widgets.growth_timeline import draw_growth
from ui.main.widgets.money_panel import draw_money
from ui.theme import COLOR, FONT


def draw_detail(c, farm, selected, hist, nights, width):
    s = farm.sections[selected]
    d, p = s.devices, s.env_state.plant_profile
    ox = 590
    c.create_text(ox, 20, anchor="w", text=f"{s.label}  상세", font=(FONT, 13, "bold"), fill=COLOR["ink"])
    c.create_text(width - 10, 20, anchor="e", font=(FONT, 9), fill=COLOR["muted"],
                  text=f"누적  물 {d.total_water_l:.0f}L · 비료 {d.total_fertilizer_g:.0f}g · "
                       f"전력 {d.total_energy_kwh:.1f}kWh (현재 {d.power_kw():.1f}kW)")
    draw_devices(c, d, ox, 48)
    draw_growth(c, s, ox, 82, width - 10)
    draw_charts(c, p, hist, nights, ox)
    c.create_text(ox, 543, anchor="w", font=(FONT, 8), fill=COLOR["muted"],
                  text="최근 24시간 · 초록 띠 = 적정 범위 · 회색 = 밤")
    draw_cctv(c, ox, 556, CHART_W, 150, s, farm, selected + 1)
    draw_money(c, farm, s, ox + CHART_W + CHART_GAP, 556, CHART_W, 150)
