"""스마트팜 프로그램 시작점. 로그인에 성공하면 관리 패널과 나머지 창을 띄운다."""
import tkinter as tk

from ui.login.window import LoginWindow
from ui.main.app import App

if __name__ == "__main__":
    root = tk.Tk()
    LoginWindow(root, on_success=lambda user: App(root, user))
    root.mainloop()
