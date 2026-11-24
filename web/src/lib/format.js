const nf = new Intl.NumberFormat("ko-KR", { maximumFractionDigits: 0 });

export const won = (v) => `${nf.format(Math.round(v))}원`;
export const signedWon = (v) => `${v >= 0 ? "+" : "−"}${nf.format(Math.abs(Math.round(v)))}원`;
export const num = (v) => nf.format(Math.round(v));

export function clock(hour) {
  const h = Math.floor(hour);
  const m = Math.floor((hour % 1) * 60);
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

/** 그래프 값 표기: 큰 값은 정수, 작은 값은 소수 둘째, 그 사이는 첫째 자리까지 */
export function metricValue(v, hi) {
  if (hi >= 1000) return nf.format(Math.round(v));
  return hi < 10 ? v.toFixed(2) : v.toFixed(1);
}

// Tailwind가 클래스 이름을 찾을 수 있게 전부 그대로 적어 둔다.
export const TONE_TEXT = {
  muted: "text-muted",
  dead: "text-dead",
  critical: "text-critical",
  ready: "text-ready",
  positive: "text-positive",
};
export const TONE_BG = {
  muted: "bg-subtle",
  dead: "bg-dead",
  critical: "bg-critical",
  ready: "bg-ready",
  positive: "bg-positive",
};

/** 건강 막대 색: 상태가 아니라 건강도 자체로 정한다 (positive → warning → critical) */
export const healthBg = (h) => (h >= 70 ? "bg-positive" : h >= 40 ? "bg-warning" : "bg-critical");

// 장치: [서버 장치 키, 이름, 켜짐 상태를 꺼내는 devices 속성]
export const DEVICES = [
  ["heater", "난방", "heater"],
  ["cooler", "냉방", "cooler"],
  ["fan", "환기", "fan"],
  ["humidifier", "가습", "humidifier"],
  ["dehumidifier", "제습", "dehumidifier"],
  ["light", "조명", "light"],
  ["irrigation", "급수", "water"],
  ["fertilizer", "비료", "fertilizer"],
];
export const DEVICE_NAMES = Object.fromEntries(DEVICES.map(([key, name]) => [key, name]));
export const MODE_NAMES = { auto: "자동", on: "켜기", off: "끄기" };

export function deviceOn(key, devices) {
  const prop = DEVICES.find((d) => d[0] === key)[2];
  return key === "light" ? devices.light > 0 : !!devices[prop];
}

export function deviceLabel(key, name, devices) {
  return key === "light" && devices.light > 0 ? `조명 ${Math.round(devices.light * 100)}%` : name;
}

// 시뮬레이션 속도: 현실 1초에 흐르는 시간(분) → 10분 진행 간격(ms)
export const SPEEDS = [
  { minutes: 10, label: "1초 = 10분" },
  { minutes: 60, label: "1초 = 1시간" },
  { minutes: 180, label: "1초 = 3시간" },
  { minutes: 480, label: "1초 = 8시간" },
].map((s) => ({ ...s, ms: Math.round(10000 / s.minutes) }));

/** 지금 속도(ms)를 사람이 읽는 말로: 하루가 현실로 몇 초인지 */
export function speedText(ms) {
  const dayMs = ms * 144;
  return dayMs >= 60000 ? `하루 = ${(dayMs / 60000).toFixed(1)}분` : `하루 = ${Math.round(dayMs / 1000)}초`;
}
