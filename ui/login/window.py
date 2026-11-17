import tkinter as tk
from tkinter import ttk, messagebox

from core.auth import Accounts
from ui.theme import COLOR, FONT


class LoginWindow(tk.Frame):
    """프로그램 첫 화면. 루트 창을 로그인 화면으로 쓰다가, 로그인에 성공하면 비우고 on_success(아이디)를 부른다."""

    def __init__(self, root, on_success, accounts: Accounts = None):
        super().__init__(root, bg=COLOR["bg"], padx=32, pady=28)
        self.root = root
        self.on_success = on_success
        self.accounts = accounts or Accounts()
        root.title("에버그로우 - 로그인")
        root.configure(bg=COLOR["bg"])
        root.resizable(False, False)
        self.pack()

        tk.Label(self, text="에버그로우 스마트팜", bg=COLOR["bg"], fg=COLOR["healthy"],
                 font=(FONT, 16, "bold")).pack(anchor="w")
        tk.Label(self, text="관리자 계정으로 로그인하세요.", bg=COLOR["bg"], fg=COLOR["muted"],
                 font=(FONT, 9)).pack(anchor="w", pady=(2, 16))

        form = tk.Frame(self, bg=COLOR["bg"])
        form.pack(fill="x")
        self.user = self._field(form, 0, "아이디")
        self.password = self._field(form, 1, "비밀번호", show="●")

        self.message = tk.Label(self, bg=COLOR["bg"], fg=COLOR["closed"], font=(FONT, 9), anchor="w")
        self.message.pack(fill="x", pady=(10, 6))

        buttons = tk.Frame(self, bg=COLOR["bg"])
        buttons.pack(fill="x")
        ttk.Button(buttons, text="종료", command=root.destroy).pack(side="right")
        ttk.Button(buttons, text="로그인", command=self.submit).pack(side="right", padx=(0, 6))

        root.bind("<Return>", lambda e: self.submit())
        self.user.focus_set()

        # 화면 가운데에 띄운다
        root.update_idletasks()
        x = (root.winfo_screenwidth() - root.winfo_reqwidth()) // 2
        y = (root.winfo_screenheight() - root.winfo_reqheight()) // 3
        root.geometry(f"+{x}+{y}")

    def _field(self, parent, row, label, show=""):
        tk.Label(parent, text=label, bg=COLOR["bg"], font=(FONT, 10), width=8, anchor="w").grid(
            row=row, column=0, sticky="w", pady=4)
        entry = ttk.Entry(parent, width=26, show=show)
        entry.grid(row=row, column=1, pady=4)
        return entry

    def submit(self):
        user_id, password = self.user.get().strip(), self.password.get()
        if not user_id or not password:
            self.message.config(text="아이디와 비밀번호를 모두 입력하세요.")
            return
        if self.accounts.login(user_id, password):
            self.root.unbind("<Return>")
            self.root.resizable(True, True)
            self.root.geometry("")
            self.destroy()
            self.on_success(user_id)
            return
        self.password.delete(0, "end")
        if self.accounts.locked:
            messagebox.showerror("로그인 잠김", f"{Accounts.MAX_FAILURES}회 연속으로 틀려 프로그램을 종료합니다.",
                                 parent=self.root)
            self.root.destroy()
            return
        self.message.config(
            text=f"아이디 또는 비밀번호가 틀렸습니다. ({self.accounts.failures}/{Accounts.MAX_FAILURES})")
        self.password.focus_set()
