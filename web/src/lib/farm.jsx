import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { api, wsUrl } from "./api.js";

const LOG_MAX = 3000;
const PRICE_MAX = 30 * 144; // 시세는 30일치까지

const FarmContext = createContext(null);
export const useFarm = () => useContext(FarmContext);

const appendCapped = (arr, more, max) => (more.length ? [...arr, ...more].slice(-max) : arr);

/** 서버가 보낸 변경분(msg)을 지금 가진 데이터에 합친다. full이면 통째로 바꾼다. */
function merge(prev, msg, historyMax) {
  if (msg.full || !prev) {
    const { state, history, nights, priceHistory, logs } = msg;
    return { state, history, nights, priceHistory, logs };
  }
  const priceHistory = {};
  for (const [name, more] of Object.entries(msg.priceHistory)) {
    priceHistory[name] = appendCapped(prev.priceHistory[name] ?? [], more, PRICE_MAX);
  }
  return {
    state: msg.state,
    history: prev.history.map((h, i) => appendCapped(h, msg.history[i], historyMax)),
    nights: appendCapped(prev.nights, msg.nights, historyMax),
    priceHistory,
    logs: appendCapped(prev.logs, msg.logs, LOG_MAX),
  };
}

/** 서버 WebSocket에 붙어서 실시간 상태를 받는다. 끊기면 1초 뒤 다시 붙는다. */
function useLive(token, onUnauthorized) {
  const [meta, setMeta] = useState(null);
  const [data, setData] = useState(null);
  const [connected, setConnected] = useState(false);
  const unauthorized = useRef(onUnauthorized);
  unauthorized.current = onUnauthorized;
  const historyMax = meta?.history ?? 144;

  useEffect(() => {
    api("/meta", { method: "GET", token })
      .then(setMeta)
      .catch((e) => e.status === 401 && unauthorized.current());
  }, [token]);

  useEffect(() => {
    let ws;
    let timer;
    let stopped = false;
    const connect = () => {
      ws = new WebSocket(wsUrl(token));
      ws.onopen = () => setConnected(true);
      ws.onmessage = (e) => {
        const msg = JSON.parse(e.data);
        setData((prev) => merge(prev, msg, historyMax));
      };
      ws.onclose = (e) => {
        setConnected(false);
        if (stopped) return;
        if (e.code === 4401) unauthorized.current();
        else timer = setTimeout(connect, 1000);
      };
    };
    connect();
    return () => {
      stopped = true;
      clearTimeout(timer);
      ws?.close();
    };
  }, [token, historyMax]);

  return { meta, data, connected };
}

export function FarmProvider({ session, onLogout, children }) {
  const { token } = session;
  const { meta, data, connected } = useLive(token, onLogout);
  const [selected, setSelected] = useState(0);
  const [crop, setCrop] = useState("상추");
  const [confirm, setConfirm] = useState(null); // { title, message, action }
  const [toast, setToast] = useState(null);
  const [alerts, setAlerts] = useState([]); // 화면 구석에 잠깐 띄우는 경고 [{seq, text, zone}]
  const [seenSeq, setSeenSeq] = useState(0); // 알림 목록을 마지막으로 열어 본 로그 번호
  const lastAlert = useRef(null);

  const sections = data?.state.sections;
  const logs = data?.logs;

  // 새 경고 로그가 들어오면 띄운다. 처음 접속했을 때 받은 옛 로그는 띄우지 않는다.
  useEffect(() => {
    if (!logs) return;
    const latest = logs.at(-1)?.seq ?? 0;
    if (lastAlert.current == null || latest < lastAlert.current) {
      lastAlert.current = latest;
      setSeenSeq((v) => (v > latest ? 0 : v));
      return;
    }
    const fresh = logs.filter((e) => e.warn && e.seq > lastAlert.current);
    lastAlert.current = latest;
    if (fresh.length) setAlerts((a) => [...a, ...fresh].slice(-3));
  }, [logs]);

  useEffect(() => {
    if (!alerts.length) return;
    const t = setTimeout(() => setAlerts((a) => a.slice(1)), 6000);
    return () => clearTimeout(t);
  }, [alerts]);

  const dismissAlert = useCallback((seq) => setAlerts((a) => a.filter((e) => e.seq !== seq)), []);

  const call = useCallback(
    async (path, opts = {}) => {
      try {
        return await api(path, { ...opts, token });
      } catch (e) {
        if (e.status === 401) onLogout();
        else setToast(e.message);
        return null;
      }
    },
    [token, onLogout],
  );

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 3200);
    return () => clearTimeout(t);
  }, [toast]);

  const select = useCallback(
    (i) => {
      setSelected(i);
      const s = sections?.[i];
      if (s) setCrop(s.species);
    },
    [sections],
  );

  const actions = useMemo(
    () => ({
      plant: (i, name) => call(`/sections/${i}/plant`, { body: { crop: name } }),
      harvest: (i) => call(`/sections/${i}/harvest`),
      harvestAll: () => call("/harvest-all"),
      pests: (i) => call(`/sections/${i}/pests`),
      step: () => call("/sim/step"),
      reset: () => call("/sim/reset"),
      setSim: (body) => call("/sim", { method: "PATCH", body }),
      setDeviceMode: (i, key, mode) => call(`/sections/${i}/devices/${key}`, { body: { mode } }),
      dose: (i, key) => call(`/sections/${i}/devices/${key}/dose`),
      updateCrop: (name, body) => call(`/crops/${encodeURIComponent(name)}`, { method: "PUT", body }),
      resetCrop: (name) => call(`/crops/${encodeURIComponent(name)}`, { method: "DELETE" }),
      notice: (text) => setToast(text),
      plow: (i) => {
        const s = sections?.[i];
        const run = () => call(`/sections/${i}/plow`);
        // 살아 있는 작물을 갈아엎을 때만 한 번 더 묻는다
        if (s?.plant?.alive) {
          setConfirm({
            title: "갈아엎기",
            message: `${s.label}의 작물(생장 ${Math.round(s.plant.growth)}%)을 수확 없이 모두 갈아엎을까요?`,
            confirmLabel: "갈아엎기",
            action: run,
          });
        } else run();
      },
    }),
    [call, sections],
  );

  const value = {
    meta,
    connected,
    user: session.user,
    logout: onLogout,
    state: data?.state,
    history: data?.history,
    nights: data?.nights,
    priceHistory: data?.priceHistory,
    logs: data?.logs ?? [],
    selected,
    select,
    crop,
    setCrop,
    actions,
    confirm,
    setConfirm,
    toast,
    alerts,
    dismissAlert,
    seenSeq,
    markSeen: () => setSeenSeq(logs?.at(-1)?.seq ?? 0),
    zoneIndex: (zone) => meta?.zones.indexOf(zone) ?? -1,
  };
  return <FarmContext.Provider value={value}>{children}</FarmContext.Provider>;
}
