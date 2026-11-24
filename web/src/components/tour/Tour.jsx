import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { useFarm } from "../../lib/farm.jsx";
import SproutBot from "./SproutBot.jsx";

// 안내 순서. target: 비출 곳(data-tour 이름, 없으면 화면 가운데에서 이야기한다)
const STEPS = [
  {
    title: "안녕하세요! 저는 새싹봇이에요",
    text: "에버그로우 스마트팜에 오신 걸 환영해요. 일손이 없어도 온실이 스스로 자라도록 돕는 곳이에요. 무엇을 할 수 있는지 제가 한 바퀴 안내해 드릴게요!",
  },
  {
    target: "greenhouse",
    title: "온실 6동을 3D로 봐요",
    text: "구역마다 온실이 한 동씩 있어요. 끌면 돌아가고, 휠로 확대하고, 온실을 누르면 그 구역으로 날아가요. 화면을 누른 뒤 W A S D로 걸어 다닐 수도 있어요. 장치에 마우스를 올리면 왜 켜졌는지도 알려 줘요. 평소엔 저도 저기서 순찰해요!",
  },
  {
    target: "cards",
    title: "구역 카드로 한눈에",
    text: "구역마다 상태, 생육 단계, 건강, 생장이 나와요. 빨간색이면 격리·방제 중, 파란 '수확 가능'이면 거둘 때예요. 카드를 누르면 오른쪽에 그 구역의 자세한 정보가 나와요.",
  },
  {
    target: "controls",
    title: "심고, 거두고, 갈아엎기",
    text: "작물 목록에는 지금 시세로 심었을 때 하루에 남는 돈이 나오고, 가장 좋은 작물을 추천해 드려요. 빈 구역에 심고, 다 자라면 수확해요. 지금 못 하는 버튼을 누르면 왜 안 되는지 알려 드려요.",
  },
  {
    target: "devices",
    title: "장치 8개는 알아서 움직여요",
    text: "난방·냉방·환기·가습·제습·조명·급수·비료가 작물의 적정 범위를 보고 스스로 켜고 꺼져요. 필요하면 '켜기·끄기'로 직접 운전하고, '자동'을 누르면 다시 맡길 수 있어요. 각 장치가 지금 왜 그 상태인지도 적혀 있어요.",
  },
  {
    target: "charts",
    title: "최근 24시간 그래프",
    text: "초록 띠는 작물에게 알맞은 범위, 회색은 밤이에요. 그래프에 마우스를 올리면 그 시각의 값이 나와요. 범위를 벗어나면 빨갛게 '범위 밖'이라고 표시돼요.",
  },
  {
    target: "harvest",
    title: "얼마나 벌었는지 확인해요",
    text: "일별 매출·비용·순이익 그래프와 수확 기록이 여기 쌓여요. 수확하는 순간엔 3D 온실에서 작물이 솟아오르고 금액이 떠올라요!",
  },
  {
    target: "simulator",
    title: "시뮬레이터로 시험해 보세요",
    text: "시간을 멈추거나 빠르게 돌리고, 계절을 건너뛰고, 한파·폭염을 걸 수 있어요. '병충해 발생시키기'를 눌러 보세요. 제가 그 온실로 달려가서 알려 드릴게요!",
  },
  {
    target: "alerts",
    title: "경고는 놓치지 않게",
    text: "병충해·고사·방제 실패 같은 경고가 생기면 화면 구석에 알림이 뜨고, 이 종에 안 읽은 개수가 붙어요. 알림을 누르면 그 구역으로 바로 가요.",
  },
  {
    target: "tabs",
    title: "다른 화면도 있어요",
    text: "'작물 시세'에서는 캔들 차트로 값의 흐름을, '작물 설정'에서는 작물별 적정 범위를, '모바일 앱'에서는 농장주용 휴대폰 화면을 볼 수 있어요.",
  },
  {
    title: "이제 직접 해 볼 차례예요!",
    text: "궁금하면 언제든 오른쪽 위 '도움말'을 눌러 주세요. 제가 다시 안내해 드릴게요. 즐거운 농사 되세요!",
  },
];

const PAD = 10; // 스포트라이트 여백
const BOT = 120;
const BUBBLE_W = 340;
const GAP = 18;
const TYPE_MS = 22; // 한 글자씩 쓰는 속도

/** 새싹봇 튜토리얼: 화면을 어둡게 하고 설명할 곳만 비추며, 새싹봇이 그 옆으로 뛰어가 말풍선으로 설명한다. */
export default function Tour({ onClose }) {
  const { user } = useFarm();
  const [step, setStep] = useState(0);
  const [rect, setRect] = useState(null); // 비추는 곳 (화면 좌표)
  const [shown, setShown] = useState(0); // 지금까지 써진 글자 수
  const next = useRef(null);
  const s = STEPS[step];
  const text = step === 0 ? `${user}님, ${s.text}` : s.text;
  const typing = shown < text.length;
  const last = step === STEPS.length - 1;

  // 단계가 바뀌면 그곳을 화면 가운데로 굴려 오고, 글자를 처음부터 쓴다
  useLayoutEffect(() => {
    setShown(0);
    const el = s.target && document.querySelector(`[data-tour="${s.target}"]`);
    if (el) el.scrollIntoView({ block: "center", behavior: "smooth" });
    next.current?.focus();
  }, [step, s.target]);

  // 레이아웃이 바뀌어도(스크롤·값 갱신) 따라가도록 매 프레임 위치를 잰다
  useEffect(() => {
    let raf;
    const measure = () => {
      const el = s.target && document.querySelector(`[data-tour="${s.target}"]`);
      const r = el?.getBoundingClientRect();
      setRect((old) => {
        if (!r) return old === null ? old : null;
        const box = { left: r.left - PAD, top: r.top - PAD, width: r.width + PAD * 2, height: r.height + PAD * 2 };
        return old && ["left", "top", "width", "height"].every((k) => Math.abs(old[k] - box[k]) < 0.5) ? old : box;
      });
      raf = requestAnimationFrame(measure);
    };
    measure();
    return () => cancelAnimationFrame(raf);
  }, [s.target]);

  useEffect(() => {
    if (!typing) return;
    const t = setTimeout(() => setShown((n) => n + 1), TYPE_MS);
    return () => clearTimeout(t);
  }, [shown, typing]);

  const go = (d) => {
    if (d > 0 && typing) return setShown(text.length); // 쓰는 중이면 먼저 다 보여 준다
    if (d > 0 && last) return onClose();
    setStep((v) => Math.min(STEPS.length - 1, Math.max(0, v + d)));
  };

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === "Escape") onClose();
      else if (e.key === "ArrowRight" || e.key === "Enter") {
        e.preventDefault();
        go(1);
      } else if (e.key === "ArrowLeft") go(-1);
    };
    addEventListener("keydown", onKey);
    return () => removeEventListener("keydown", onKey);
  });

  const place = botPlace(rect);

  return (
    <div className="fixed inset-0 z-[80]" role="dialog" aria-modal="true" aria-label="새싹봇 사용 안내">
      {/* 어두운 막: 비추는 곳만 뚫린 것처럼 보이게 큰 그림자를 쓴다 (안내 중엔 아래 화면을 누를 수 없다) */}
      <div
        className="absolute rounded-2xl ring-2 ring-brand transition-all duration-500 ease-out"
        style={
          rect
            ? { ...px(rect), boxShadow: "0 0 0 9999px rgb(10 14 18 / 0.62)" }
            : { left: "50%", top: "50%", width: 0, height: 0, boxShadow: "0 0 0 9999px rgb(10 14 18 / 0.62)", border: 0 }
        }
      />

      {/* 새싹봇 + 말풍선: 비추는 곳 옆으로 뛰어간다 */}
      <div
        className="absolute flex items-end gap-1 transition-[left,top] duration-700 ease-[cubic-bezier(.3,1.4,.5,1)]"
        style={{ left: place.left, top: place.top, flexDirection: place.flip ? "row-reverse" : "row" }}
      >
        <div key={step} className="bot-hop shrink-0">
          <SproutBot talking={typing} size={BOT} />
        </div>
        <div className="relative mb-10 rounded-2xl bg-card p-4 text-ink shadow-2xl ring-2 ring-brand" style={{ width: BUBBLE_W }}>
          <span
            aria-hidden
            className={`absolute bottom-6 size-4 rotate-45 bg-card ${place.flip ? "-right-2 border-r-2 border-t-2" : "-left-2 border-b-2 border-l-2"} border-brand`}
          />
          <p className="text-xs font-bold text-brand-pressed">
            새싹봇 · {step + 1} / {STEPS.length}
          </p>
          <h2 className="mt-1 text-base font-bold">{s.title}</h2>
          <p className="mt-1.5 min-h-24 text-sm leading-relaxed text-muted" aria-hidden>
            {text.slice(0, shown)}
            {typing && <span className="ml-0.5 inline-block h-3.5 w-0.5 animate-pulse bg-brand align-middle" />}
          </p>
          <p className="sr-only" aria-live="polite">
            {text}
          </p>
          <div className="mt-3 flex items-center gap-2">
            <button onClick={onClose} className="mr-auto text-xs text-subtle hover:text-ink">
              건너뛰기
            </button>
            {step > 0 && (
              <button onClick={() => go(-1)} className="rounded-lg px-3 py-1.5 text-sm ring-1 ring-line hover:bg-pressed">
                이전
              </button>
            )}
            <button ref={next} onClick={() => go(1)} className="rounded-lg bg-brand px-4 py-1.5 text-sm font-bold text-white hover:bg-brand-pressed">
              {typing ? "다 보기" : last ? "시작하기" : "다음"}
            </button>
          </div>
          <div className="mt-3 flex justify-center gap-1" aria-hidden>
            {STEPS.map((_, i) => (
              <span key={i} className={`h-1.5 rounded-full transition-all ${i === step ? "w-5 bg-brand" : "w-1.5 bg-line"}`} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

const px = (r) => ({ left: r.left, top: r.top, width: r.width, height: r.height });

/** 새싹봇+말풍선 자리: 비추는 곳의 오른쪽 → 왼쪽 → 아래 → 위 중 화면 안에 들어가는 곳. 없으면 가운데. */
function botPlace(rect) {
  const W = BOT + BUBBLE_W + 4;
  const H = 300;
  const vw = innerWidth;
  const vh = innerHeight;
  const clampX = (x) => Math.min(vw - W - 12, Math.max(12, x));
  const clampY = (y) => Math.min(vh - H - 12, Math.max(12, y));
  if (!rect) return { left: (vw - W) / 2, top: (vh - H) / 2, flip: false };
  const right = rect.left + rect.width;
  const bottom = rect.top + rect.height;
  const midY = clampY(rect.top + rect.height / 2 - H / 2);
  if (right + GAP + W < vw - 12) return { left: right + GAP, top: midY, flip: false };
  if (rect.left - GAP - W > 12) return { left: rect.left - GAP - W, top: midY, flip: true };
  if (bottom + GAP + H < vh - 12) return { left: clampX(rect.left + rect.width / 2 - W / 2), top: bottom + GAP, flip: false };
  if (rect.top - GAP - H > 12) return { left: clampX(rect.left + rect.width / 2 - W / 2), top: rect.top - GAP - H, flip: false };
  return { left: vw - W - 16, top: vh - H - 16, flip: false }; // 큰 영역이면 화면 오른쪽 아래 구석에서
}
