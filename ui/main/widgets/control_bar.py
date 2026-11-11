"""관리 패널 버튼 줄: 작물 고르기, 심기·수확·갈아엎기, 자동 재파종, 다른 창 열기"""
import tkinter as tk
from tkinter import ttk

from core.catalog import PROFILES
from ui.theme import COLOR, FONT


class ControlBar:
    def __init__(self, root, app):
        bar = tk.Frame(root, bg=COLOR["bg"])
        bar.pack(fill="x", padx=12)
        tk.Label(bar, text="선택 구역 작물", bg=COLOR["bg"], font=(FONT, 9)).pack(side="left", padx=(0, 4))
        self.crop = ttk.Combobox(bar, values=[p[0] for p in PROFILES], state="readonly", width=8)
        self.crop.current(0)
        self.crop.pack(side="left")
        ttk.Button(bar, text="🌱 심기", command=app.plant).pack(side="left", padx=4)
        ttk.Button(bar, text="🧺 수확 / 정리", command=app.harvest).pack(side="left")
        ttk.Button(bar, text="수확 가능한 구역 모두 수확", command=app.harvest_all).pack(side="left", padx=4)
        ttk.Button(bar, text="🚜 갈아엎기", command=app.plow).pack(side="left")
        self.auto_replant = tk.BooleanVar(value=True)
        ttk.Checkbutton(bar, text="수확 후 자동 재파종 (시세 최고 작물)", variable=self.auto_replant,
                        command=app.apply_auto_replant).pack(side="left", padx=8)
        ttk.Button(bar, text="📈 시세", command=lambda: app.show(app.prices)).pack(side="right")
        ttk.Button(bar, text="📹 CCTV 전체", command=lambda: app.show(app.cctv)).pack(side="right")
        ttk.Button(bar, text="⚙ 시뮬레이터 창", command=lambda: app.show(app.sim)).pack(side="right")
        ttk.Button(bar, text="📱 모바일 앱", command=lambda: app.show(app.mobile)).pack(side="right", padx=4)
