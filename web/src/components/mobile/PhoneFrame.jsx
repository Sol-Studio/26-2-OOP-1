import MobileApp from "./MobileApp.jsx";

/** 데스크톱에서 모바일 앱을 휴대폰 크기(9:16)로 보여 준다. 휴대폰으로 접속하면 이 틀 없이 바로 뜬다. */
export default function PhoneFrame() {
  return (
    <div className="flex flex-wrap items-start justify-center gap-10 py-4">
      <div className="h-[720px] w-[380px] shrink-0 overflow-hidden rounded-[2.5rem] border-[10px] border-dark bg-bg shadow-xl">
        <MobileApp />
      </div>
      <div className="max-w-xs pt-8 text-sm text-muted">
        <h2 className="mb-2 text-base font-bold text-ink">농장주용 모바일 앱</h2>
        <p>관리 패널과 같은 농장을 실시간으로 봅니다. 구역 선택도 서로 따라갑니다.</p>
      </div>
    </div>
  );
}
