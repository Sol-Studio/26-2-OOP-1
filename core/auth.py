"""로그인 계정 확인. 비밀번호는 원문 대신 솔트와 해시로만 저장한다."""
import hashlib
import hmac
import os

ITERATIONS = 100_000

# 아이디: (솔트, 비밀번호 해시) — 기본 계정 farmer / evergrow
DEFAULT_USERS = {
    "farmer": ("846aaf8f01cb43e630f0e80d2e3553be",
               "c4162e0c7c82acc086ec3c12236ba8679f98be21d7388b12318af4d2902dee1a"),
}


def hash_password(password: str, salt: bytes = None) -> tuple:
    """(솔트, 해시)를 16진수 문자열로 돌려준다. 솔트를 안 주면 새로 만든다."""
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return salt.hex(), digest.hex()


class Accounts:
    """계정 목록과 로그인 실패 횟수. 연속으로 MAX_FAILURES번 틀리면 잠긴다."""
    MAX_FAILURES = 5

    def __init__(self, users: dict = None):
        self.users = dict(DEFAULT_USERS if users is None else users)
        self.failures = 0

    @property
    def locked(self):
        return self.failures >= self.MAX_FAILURES

    def add(self, user_id: str, password: str):
        self.users[user_id] = hash_password(password)

    def login(self, user_id: str, password: str) -> bool:
        if self.locked:
            return False
        record = self.users.get(user_id)
        ok = record is not None and hmac.compare_digest(
            hash_password(password, bytes.fromhex(record[0]))[1], record[1])
        self.failures = 0 if ok else self.failures + 1
        return ok
