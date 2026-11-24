import { Suspense, lazy, useEffect, useRef, useState } from "react";
import { api } from "../lib/api.js";
import { useReducedMotion } from "../lib/motion.js";
import SproutBot from "./tour/SproutBot.jsx";

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
  const [leapFrom, setLeapFrom] = useState(null); // 새싹봇이 지구본에서 뛰어내린 화면 위치
  const form = useRef(null);
  const farmScreen = useRef(null); // 지구본의 농장 점 화면 위치 (지구본이 매 프레임 알려 준다)
  const [returning, setReturning] = useState(null); // 로그인 성공 뒤 새싹봇이 지구본으로 돌아가는 중인 세션

  // 새싹봇이 돌아가는 연출이 끝나지 않아도 들어가지도록 안전장치
  useEffect(() => {
    if (!returning || entering) return;
    const t = setTimeout(() => setEntering(returning), 2500);
    return () => clearTimeout(t);
  }, [returning, entering]);

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
      // 새싹봇이 로그인 창 위에 있으면 먼저 지구본으로 뛰어올라 간 뒤 들어간다
      if (wide && !still && leapFrom) setReturning(session);
      else if (wide && !still) setEntering(session);
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
              <LoginGlobe
                dive={!!entering}
                onDived={() => onLogin(entering)}
                onLeap={setLeapFrom}
                farmScreen={farmScreen}
                returning={!!returning}
                botHome={!!entering}
              />
            </Suspense>
          </div>
          <div className={`pointer-events-none absolute inset-x-0 top-0 p-10 transition-opacity duration-500 ${entering || returning ? "opacity-0" : ""}`}>
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
        className={`grid min-h-dvh place-items-center px-4 py-10 transition duration-500 ${entering || returning ? "pointer-events-none translate-x-6 opacity-0" : ""}`}
      >
      <form ref={form} onSubmit={submit} className="w-full max-w-sm px-2">
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
      {leapFrom && !entering && (
        <FormBot from={leapFrom} form={form} goHome={returning ? farmScreen : null} onHome={() => setEntering(returning)} />
      )}
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

const FLY = 1.0; // 지구본에서 로그인 창까지 날아가는 시간 (초)
const WALK = 80; // 로그인 창 위를 걷는 속도 (px/초)
const lerp = (a, b, t) => a + (b - a) * t;

/** 지구본에서 뛰어내린 새싹봇: 공중제비를 돌며 로그인 창 위로 날아가 착지하고,
 *  "여기서 로그인해 볼까요?" 한마디 한 뒤 창 위쪽 가장자리를 좌우로 통통 뛰어다닌다. */
function FormBot({ from, form, goHome, onHome }) {
  const outer = useRef(null);
  const inner = useRef(null);
  const [say, setSay] = useState(false);
  // 로그인에 성공하면 지구본 농장 점으로 다시 뛰어오른다 (그리는 함수가 최신 값을 보도록 ref로)
  const home = useRef({ target: null, onHome: null });
  home.current.target = goHome;
  home.current.onHome = onHome;

  useEffect(() => {
    let raf;
    let last = performance.now();
    const start = last;
    const walk = { x: null, dir: 1 };
    let landed = false;
    let back = null; // 돌아가기 시작한 { t, x, y }
    let pos = { x: from.x, y: from.y };
    const tick = (now) => {
      raf = requestAnimationFrame(tick);
      const r = form.current?.getBoundingClientRect();
      if (!r || !outer.current || !inner.current) return;
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      const t = (now - start) / 1000;
      const land = { x: r.left + 70, y: r.top - 6 };
      let x, y, turn = 0, flip = false, squash = 1, size;
      const goal = home.current.target?.current;
      if (goal && !back) back = { t, x: pos.x, y: pos.y };
      if (back) {
        // 지구본으로 뛰어오르며 공중제비, 착지하면 지구본 새싹봇이 이어받는다
        const u = Math.min(1, (t - back.t) / FLY);
        x = lerp(back.x, goal.x, u);
        y = lerp(back.y, goal.y, u) - Math.sin(Math.PI * u) * 260;
        turn = -u * 360;
        flip = goal.x < back.x;
        size = lerp(1, 0.75, u);
        if (u >= 1) {
          cancelAnimationFrame(raf);
          outer.current.style.opacity = "0";
          home.current.onHome?.();
          return;
        }
      } else if (t < FLY) {
        // 포물선을 그리며 날아가면서 한 바퀴 공중제비
        const u = t / FLY;
        x = lerp(from.x, land.x, u);
        y = lerp(from.y, land.y, u) - Math.sin(Math.PI * u) * 240;
        turn = u * 360;
        size = lerp(0.75, 1, u);
      } else {
        if (!landed) {
          landed = true;
          walk.x = land.x;
          setSay(true);
          setTimeout(() => setSay(false), 3500);
        }
        const tt = t - FLY;
        // 착지하고 잠깐 말한 뒤 걷기 시작한다. 창 끝에 닿으면 돌아선다.
        if (tt > 1.2) {
          walk.x += walk.dir * WALK * dt;
          const lo = r.left + 30;
          const hi = r.right - 30;
          if (walk.x > hi) [walk.x, walk.dir] = [hi, -1];
          if (walk.x < lo) [walk.x, walk.dir] = [lo, 1];
        }
        const hop = Math.abs(Math.sin(tt * 6.5));
        const big = Math.floor(tt / 0.48) % 6 === 5 ? 2.4 : 1; // 가끔 크게 뛴다
        x = walk.x;
        y = r.top - 6 - hop * 16 * big;
        squash = 1 - 0.18 * Math.max(0, 1 - hop * 4); // 땅에 닿을 때 찌그러진다
        flip = walk.dir < 0;
        size = 1;
      }
      pos = { x, y };
      outer.current.style.transform = `translate(${x}px, ${y}px) translate(-50%, -100%)`;
      inner.current.style.transform = `rotate(${turn}deg) scale(${(flip ? -1 : 1) * size / Math.sqrt(squash)}, ${size * squash})`;
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [from, form]);

  return (
    <div
      ref={outer}
      aria-hidden
      className="pointer-events-none fixed left-0 top-0 z-40"
    >
      {say && (
        <p className="absolute bottom-full left-1/2 mb-1 -translate-x-1/2 whitespace-nowrap rounded-xl bg-card px-3 py-1.5 text-xs font-bold text-ink shadow-lg">
          여기서 로그인해 볼까요?
        </p>
      )}
      <div ref={inner} style={{ transformOrigin: "50% 100%" }}>
        <SproutBot size={56} talking={say} />
      </div>
    </div>
  );
}
