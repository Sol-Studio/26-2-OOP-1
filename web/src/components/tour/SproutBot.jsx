/** 새싹봇 2D 그림 (튜토리얼용). 3D 새싹봇과 같은 모습: 흰 동그란 몸, 머리 위 새싹, 검은 얼굴 화면에 초록 눈, 주황 띠와 발.
 *  talking이면 오른팔을 흔든다. 숨쉬듯 들썩이고 눈을 깜빡이는 움직임은 index.css의 bot-* 애니메이션. */
export default function SproutBot({ talking = false, size = 120 }) {
  return (
    <svg viewBox="0 0 120 140" width={size} height={(size * 140) / 120} aria-hidden className="bot-bob overflow-visible drop-shadow-lg">
      <ellipse cx="60" cy="134" rx="30" ry="5" fill="#000" opacity="0.25" />
      {/* 다리와 발 */}
      <rect x="44" y="104" width="9" height="20" rx="4" fill="#c9ced4" />
      <rect x="67" y="104" width="9" height="20" rx="4" fill="#c9ced4" />
      <ellipse cx="48" cy="126" rx="10" ry="6" fill="#ff6600" />
      <ellipse cx="72" cy="126" rx="10" ry="6" fill="#ff6600" />
      {/* 왼팔 */}
      <rect x="14" y="66" width="12" height="30" rx="6" fill="#f6f7f9" stroke="#dcdee3" transform="rotate(18 20 68)" />
      {/* 오른팔: 말할 때 흔든다 */}
      <g className={talking ? "bot-wave" : ""} style={{ transformOrigin: "98px 68px" }}>
        <rect x="94" y="66" width="12" height="30" rx="6" fill="#f6f7f9" stroke="#dcdee3" transform="rotate(-18 100 68)" />
      </g>
      {/* 몸통 */}
      <circle cx="60" cy="72" r="40" fill="#f6f7f9" stroke="#dcdee3" strokeWidth="1.5" />
      <path d="M22 84 Q60 98 98 84" fill="none" stroke="#ff6600" strokeWidth="6" strokeLinecap="round" />
      {/* 얼굴 화면, 눈, 입 */}
      <ellipse cx="60" cy="64" rx="27" ry="18" fill="#1d242c" />
      <g className="bot-blink" style={{ transformOrigin: "60px 62px" }}>
        <rect x="46" y="55" width="7" height="13" rx="3.5" fill="#5fe0a8" />
        <rect x="67" y="55" width="7" height="13" rx="3.5" fill="#5fe0a8" />
      </g>
      {talking ? (
        <ellipse className="bot-talk" cx="60" cy="74" rx="5" ry="3" fill="#5fe0a8" style={{ transformOrigin: "60px 74px" }} />
      ) : (
        <path d="M53 73 Q60 78 67 73" fill="none" stroke="#5fe0a8" strokeWidth="2.5" strokeLinecap="round" />
      )}
      {/* 머리 위 새싹 */}
      <g className="bot-sprout" style={{ transformOrigin: "60px 34px" }}>
        <path d="M60 34 V18" stroke="#3f9b4c" strokeWidth="3.5" strokeLinecap="round" />
        <ellipse cx="50" cy="16" rx="11" ry="5.5" fill="#5cc463" transform="rotate(-25 50 16)" />
        <ellipse cx="70" cy="16" rx="11" ry="5.5" fill="#5cc463" transform="rotate(25 70 16)" />
      </g>
    </svg>
  );
}
