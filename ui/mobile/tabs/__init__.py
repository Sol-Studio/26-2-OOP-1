"""모바일 앱 탭 목록. 탭을 더하려면 파일을 만들고 여기에 등록한다."""
from ui.mobile.tabs.alerts import draw_alerts
from ui.mobile.tabs.cctv import draw_cctv
from ui.mobile.tabs.home import draw_home
from ui.mobile.tabs.zone import draw_zone

TABS = [("home", "홈"), ("cctv", "CCTV"), ("zone", "구역"), ("alerts", "알림")]
DRAW = {"home": draw_home, "cctv": draw_cctv, "zone": draw_zone, "alerts": draw_alerts}
