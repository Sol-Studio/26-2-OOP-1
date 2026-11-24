// 서버 REST 호출. 로그인 토큰은 탭을 닫으면 사라지도록 sessionStorage에 둔다.
const TOKEN_KEY = "evergrow.session";

export function loadSession() {
  try {
    return JSON.parse(sessionStorage.getItem(TOKEN_KEY));
  } catch {
    return null;
  }
}

export function saveSession(session) {
  try {
    if (session) sessionStorage.setItem(TOKEN_KEY, JSON.stringify(session));
    else sessionStorage.removeItem(TOKEN_KEY);
  } catch {
    /* 저장이 막힌 브라우저면 이번 탭에서만 로그인 상태를 유지한다 */
  }
}

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

export async function api(path, { method = "POST", body, token } = {}) {
  const res = await fetch(`/api${path}`, {
    method,
    headers: {
      ...(body ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = typeof data.detail === "string" ? data.detail : "요청을 처리하지 못했습니다.";
    throw new ApiError(res.status, detail);
  }
  return data;
}

export function wsUrl(token) {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  return `${proto}://${location.host}/api/ws?token=${encodeURIComponent(token)}`;
}
