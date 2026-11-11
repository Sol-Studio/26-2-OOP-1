"""로그 창: 구역별로 걸러 보기 (구역 표시가 없는 날씨 등 공통 로그는 항상 보인다)"""
import re
import tkinter as tk
from collections import deque
from tkinter import ttk

from core.catalog import ZONES
from ui.theme import COLOR, FONT


class LogPanel:
    MAX_LINES = 500

    def __init__(self, root):
        bar = tk.Frame(root, bg=COLOR["bg"])
        bar.pack(fill="x", padx=12, pady=(6, 0))
        tk.Label(bar, text="로그", bg=COLOR["bg"], font=(FONT, 9, "bold")).pack(side="left", padx=(0, 6))
        self.filter = tk.StringVar(value="전체")
        for name in ["전체"] + ZONES:
            ttk.Radiobutton(bar, text=name, value=name, variable=self.filter, style="Toolbutton",
                            command=self.refill).pack(side="left", padx=1)
        self.entries = deque(maxlen=3000)     # (구역, 글, 경고 여부)

        self.listbox = tk.Listbox(root, height=7, font=(FONT, 9), bg="#18201b", fg="#d6e6d9",
                                  selectbackground="#2f6b45", borderwidth=0, highlightthickness=0)
        self.listbox.pack(fill="both", expand=True, padx=12, pady=(4, 12))

    def clear(self):
        self.entries.clear()
        self.listbox.delete(0, "end")

    def write(self, text, warn=False):
        m = re.search(r"구역\d+", text)
        entry = (m.group() if m else None, text, warn)
        self.entries.append(entry)
        if self.shows(entry[0]):
            self.add_line(entry)
            if self.listbox.size() > self.MAX_LINES:
                self.listbox.delete(0)
            self.listbox.see("end")

    def shows(self, zone):
        f = self.filter.get()
        return f == "전체" or zone is None or zone == f

    def add_line(self, entry):
        _, text, warn = entry
        self.listbox.insert("end", text)
        if warn:
            self.listbox.itemconfig("end", fg="#f4a97c")

    def refill(self):
        self.listbox.delete(0, "end")
        for entry in [e for e in self.entries if self.shows(e[0])][-self.MAX_LINES:]:
            self.add_line(entry)
        self.listbox.see("end")

    def follow_zone(self, index):
        """구역 로그를 보는 중이면 선택한 구역으로 바꾼다."""
        if self.filter.get() != "전체":
            self.filter.set(ZONES[index])
            self.refill()
