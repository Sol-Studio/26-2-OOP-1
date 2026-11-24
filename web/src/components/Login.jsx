import { Suspense, lazy, useEffect, useState } from "react";
import { api } from "../lib/api.js";
import { useReducedMotion } from "../lib/motion.js";

// 지구본(three.js)은 넓은 화면에서만, 따로 받아 온다
const LoginGlobe = lazy(() => import("./three/LoginGlobe.jsx"));
const WIDE = "(min-width: 1024px)";
const GLOBE_WIDTH = "54%"; // 넓은 화면에서 지구본이 차지하는 왼쪽 폭

function useWide() {
  const [wide, setWide] = useState(() => matchMedia(WIDE).matches);
  useEffect(() => {
    const mq = matchMedia(WIDE);
    const on = () => setWide(mq.matches);
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);
  return wide;
}

/** 첫 화면: 왼쪽은 돌아가는 지구본, 오른쪽은 로그인 창. 5번 연속 틀리면 서버가 로그인을 잠근다. */
export default function Login({ onLogin }) {
  const wide = useWide();
  const still = useReducedMotion();
  const [entering, setEntering] = useState(null); // 로그인에 성공해 농장으로 들어가는 중인 세션

  // 지구본이 늦게 뜨거나 그리지 못해도 들어가지도록 안전장치
  useEffect(() => {
    if (!entering) return;
    const t = setTimeout(() => onLogin(entering), 3000);
    return () => clearTimeout(t);
  }, [entering, onLogin]);
  const [user, setUser] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [locked, setLocked] = useState(false);
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    if (!user.trim() || !password) {
      setMessage("아이디와 비밀번호를 모두 입력하세요.");
      return;
    }
    setBusy(true);
    try {
      const session = await api("/login", { body: { user, password } });
      // 넓은 화면이면 지구본의 농장으로 빨려 들어간 뒤에 들어간다
      if (wide && !still) setEntering(session);
      else onLogin(session);
    } catch (err) {
      setPassword("");
      setMessage(err.message);
      setLocked(err.status === 423);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="relative min-h-full overflow-x-hidden bg-[radial-gradient(circle_at_30%_50%,#24303c_0%,#11171d_45%,#0b0f13_100%)]">
      {wide && (
        /* 들어갈 때 지구본 칸이 화면 전체로 넓어져서, 농장 점이 화면 한가운데로 빨려 들어간다 */
        <aside className="absolute inset-y-0 left-0 overflow-hidden transition-[width] duration-700 ease-out" style={{ width: entering ? "100%" : GLOBE_WIDTH }}>
          <div className="absolute inset-0">
            <Suspense fallback={null}>
              <LoginGlobe dive={!!entering} onDived={() => onLogin(entering)} />
            </Suspense>
          </div>
          <div className={`pointer-events-none absolute inset-x-0 top-0 p-10 transition-opacity duration-500 ${entering ? "opacity-0" : ""}`}>
            <p className="text-sm font-bold text-brand">EverGrow Smart Farm</p>
            <h2 className="mt-2 max-w-md text-3xl font-bold leading-snug text-white">
              일손이 줄어도,
              <br />
              온실은 스스로 자랍니다.
            </h2>
          </div>
          <p className="pointer-events-none absolute bottom-8 left-10 flex items-center gap-2 text-sm text-dark-text">
            <span className="size-2 rounded-full bg-white" aria-hidden /> 에버그로우 농장 · 대한민국
          </p>
        </aside>
      )}
      <main
        style={wide ? { marginLeft: GLOBE_WIDTH } : undefined}
        className={`grid min-h-dvh place-items-center px-4 py-10 transition duration-500 ${entering ? "pointer-events-none translate-x-6 opacity-0" : ""}`}
      >
      <form onSubmit={submit} className="w-full max-w-sm px-2">
        <div className="mb-6 flex items-center gap-3">
          <img src="/favicon.svg" alt="" className="size-10" />
          <div>
            <h1 className="text-lg font-bold text-white">에버그로우 스마트팜</h1>
            <p className="text-sm text-dark-text/70">관리자 계정으로 로그인하세요.</p>
          </div>
        </div>

        <label className="mb-1 block text-sm font-medium text-dark-text" htmlFor="user">아이디</label>
        <input
          id="user"
          autoFocus
          autoComplete="username"
          value={user}
          onChange={(e) => setUser(e.target.value)}
          disabled={locked}
          className="mb-4 w-full rounded-lg border border-white/15 bg-white/5 px-3 py-2.5 text-sm text-white outline-none placeholder:text-white/30 focus:border-brand focus:ring-2 focus:ring-brand/30 disabled:opacity-50"
        />
        <label className="mb-1 block text-sm font-medium text-dark-text" htmlFor="password">비밀번호</label>
        <input
          id="password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          disabled={locked}
          className="w-full rounded-lg border border-white/15 bg-white/5 px-3 py-2.5 text-sm text-white outline-none placeholder:text-white/30 focus:border-brand focus:ring-2 focus:ring-brand/30 disabled:opacity-50"
        />

        <p role="alert" className="mt-3 min-h-5 text-sm text-[#ff7b74]">{message}</p>

        <button
          type="submit"
          disabled={busy || locked}
          className="mt-3 w-full rounded-lg bg-brand py-2.5 text-sm font-bold text-white transition-colors hover:bg-brand-pressed disabled:cursor-not-allowed disabled:bg-white/15 disabled:text-white/60"
        >
          {locked ? "로그인 잠김" : busy ? "확인 중…" : "로그인"}
        </button>
        <p className="mt-4 text-center text-xs text-dark-text/50">기본 계정 farmer / evergrow</p>
      </form>
      </main>
      {/* 농장에 다 들어갈 즈음 화면이 밝아지며 관리 패널로 넘어간다 */}
      <div
        aria-hidden
        className={`pointer-events-none fixed inset-0 z-50 bg-bg transition-opacity duration-500 ${
          entering ? "opacity-100 delay-[1300ms]" : "opacity-0"
        }`}
      />
    </div>
  );
}
