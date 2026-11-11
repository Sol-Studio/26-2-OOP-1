"""스마트팜 관리 패널을 띄우는 시작점"""
import tkinter as tk

from ui.main.app import App

if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
