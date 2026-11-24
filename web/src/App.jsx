import { Suspense, lazy, useCallback, useEffect, useState } from "react";
import { api, loadSession, saveSession } from "./lib/api.js";
import { FarmProvider, useFarm } from "./lib/farm.jsx";
import Login from "./components/Login.jsx";
import TopBar from "./components/TopBar.jsx";
import SimulatorBar from "./components/SimulatorBar.jsx";
import Dashboard from "./components/Dashboard.jsx";
import PhoneFrame from "./components/mobile/PhoneFrame.jsx";
import MobileApp from "./components/mobile/MobileApp.jsx";
import ConfirmDialog from "./components/ConfirmDialog.jsx";
import { AlertToasts } from "./components/Alerts.jsx";
import { useReducedMotion } from "./lib/motion.js";
import Tour from "./components/tour/Tour.jsx";

// 사용 안내를 이미 본 계정 (이 브라우저에서만 기억한다)
const TOUR_KEY = (user) => `evergrow.tour.${user}`;
function tourSeen(user) {
  try {
    return localStorage.getItem(TOUR_KEY(user)) === "1";
  } catch {
    return false;
  }
}
function markTourSeen(user) {
  try {
    localStorage.setItem(TOUR_KEY(user), "1");
  } catch {
    /* 저장이 막혀 있으면 다음 로그인 때 다시 보여 줄 뿐이다 */
  }
}

// chart.js는 시세 화면을 열 때 따로 받는다
const PricePanel = lazy(() => import("./components/PricePanel.jsx"));
const CropSettings = lazy(() => import("./components/CropSettings.jsx"));

export default function App() {
  const [session, setSession] = useState(loadSession);
  const [intro, setIntro] = useState(false); // 방금 로그인했으면 첫 화면 연출을 한 번 보여 준다

  const logout = useCallback(() => {
    const token = loadSession()?.token;
    if (token) api("/logout", { token }).catch(() => {});
    saveSession(null);
    setSession(null);
  }, []);

  const login = (s) => {
    saveSession(s);
    setSession(s);
    setIntro(true);
  };

  if (!session) return <Login onLogin={login} />;
  return (
    <FarmProvider session={session} onLogout={logout}>
      <Shell intro={intro} onIntroEnd={() => setIntro(false)} />
    </FarmProvider>
  );
}

function useNarrow() {
  const query = "(max-width: 767px)";
  const [narrow, setNarrow] = useState(() => matchMedia(query).matches);
  useEffect(() => {
    const mq = matchMedia(query);
    const on = () => setNarrow(mq.matches);
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);
  return narrow;
}

function Shell({ intro, onIntroEnd }) {
  const { state, toast, user } = useFarm();
  const [view, setView] = useState("panel");
  const narrow = useNarrow();
  const still = useReducedMotion();
  const introOn = intro && !still && !narrow; // 첫 화면 연출이 실제로 재생되는지
  const [tour, setTour] = useState(false);

  // 처음 로그인했으면 첫 화면 연출이 끝난 뒤 새싹봇이 사용법을 안내한다 (휴대폰 폭은 화면 구성이 달라 생략)
  useEffect(() => {
    if (state && !narrow && !introOn && !tourSeen(user)) {
      setView("panel");
      setTour(true);
    }
  }, [!!state, narrow, introOn, user]); // eslint-disable-line react-hooks/exhaustive-deps

  const openTour = () => {
    setView("panel");
    setTour(true);
  };
  const closeTour = () => {
    markTourSeen(user);
    setTour(false);
  };

  if (!state) {
    return (
      <div className="grid h-full place-items-center text-sm text-muted">
        <p>농장에 연결하는 중…</p>
      </div>
    );
  }

  // 휴대폰 화면 폭이면 모바일 앱을 그대로 띄운다
  if (narrow) {
    return (
      <div className="h-dvh">
        <MobileApp />
        <AlertToasts />
        <ConfirmDialog />
        <Toast text={toast} />
      </div>
    );
  }

  return (
    <div className="min-h-full">
      <TopBar view={view} setView={setView} onHelp={openTour} />
      <SimulatorBar />
      <main className="mx-auto max-w-[1600px] px-4 pb-6 pt-4 lg:px-6">
        {view === "panel" && <Dashboard intro={introOn} onIntroEnd={onIntroEnd} />}
        {view === "prices" && (
          <Suspense fallback={<p className="py-10 text-center text-sm text-muted">시세 화면을 불러오는 중…</p>}>
            <PricePanel />
          </Suspense>
        )}
        {view === "crops" && (
          <Suspense fallback={null}>
            <CropSettings />
          </Suspense>
        )}
        {view === "mobile" && <PhoneFrame />}
      </main>
      <AlertToasts />
      <ConfirmDialog />
      <Toast text={toast} />
      {tour && <Tour onClose={closeTour} />}
    </div>
  );
}

function Toast({ text }) {
  if (!text) return null;
  return (
    <div role="status" className="fixed bottom-5 left-1/2 z-50 -translate-x-1/2 rounded-lg bg-dark px-4 py-2.5 text-sm text-white shadow-lg">
      {text}
    </div>
  );
}
