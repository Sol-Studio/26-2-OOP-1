"""EverGrow 웹 서버. 시뮬레이션을 계속 돌리고, 웹 화면에 상태를 WebSocket으로 밀어 준다.
조작(심기·수확·속도 등)은 REST로 받는다. web/dist가 있으면 빌드된 화면도 같이 내보낸다."""
import asyncio
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from core.auth import Accounts
from core.catalog import PROFILES
from core.weather import SEASONS
from server.simulation import CROPS, WEATHER, Simulation

WEB_DIST = Path(__file__).resolve().parent.parent / "web" / "dist"
SEND_INTERVAL = 1 / 30          # 한 연결에 보내는 최소 간격 (그 사이 변경은 한 번에 묶어 보낸다)

sim = Simulation()
accounts = Accounts()
sessions: dict[str, str] = {}   # 토큰 → 아이디


@asynccontextmanager
async def lifespan(_: FastAPI):
    task = asyncio.create_task(sim.run_forever())
    yield
    task.cancel()


app = FastAPI(title="EverGrow 스마트팜", lifespan=lifespan)


# ---------- 로그인 ----------
class LoginBody(BaseModel):
    user: str
    password: str


@app.post("/api/login")
async def login(body: LoginBody):
    user_id = body.user.strip()
    if not user_id or not body.password:
        raise HTTPException(400, "아이디와 비밀번호를 모두 입력하세요.")
    if accounts.locked:
        raise HTTPException(423, f"{Accounts.MAX_FAILURES}회 연속으로 틀려 로그인이 잠겼습니다. 서버를 다시 시작하세요.")
    if not accounts.login(user_id, body.password):
        if accounts.locked:
            raise HTTPException(423, f"{Accounts.MAX_FAILURES}회 연속으로 틀려 로그인이 잠겼습니다. 서버를 다시 시작하세요.")
        raise HTTPException(401, f"아이디 또는 비밀번호가 틀렸습니다. ({accounts.failures}/{Accounts.MAX_FAILURES})")
    token = secrets.token_urlsafe(24)
    sessions[token] = user_id
    return dict(token=token, user=user_id)


def current_user(authorization: str = Header("")) -> str:
    token = authorization.removeprefix("Bearer ").strip()
    if token not in sessions:
        raise HTTPException(401, "로그인이 필요합니다.")
    return sessions[token]


@app.post("/api/logout", dependencies=[Depends(current_user)])
async def logout(authorization: str = Header("")):
    sessions.pop(authorization.removeprefix("Bearer ").strip(), None)
    return dict(ok=True)


@app.get("/api/me")
async def me(user: str = Depends(current_user)):
    return dict(user=user)


# 아래 경로는 모두 로그인이 필요하다
protected = APIRouter(prefix="/api", dependencies=[Depends(current_user)])


@protected.get("/meta")
async def meta():
    return Simulation.meta()


# ---------- 구역 조작 ----------
def section_index(index: int) -> int:
    if not 0 <= index < len(sim.farm.sections):
        raise HTTPException(404, "없는 구역입니다.")
    return index


class PlantBody(BaseModel):
    crop: str


@protected.post("/sections/{index}/plant")
async def plant(body: PlantBody, index: int = Depends(section_index)):
    if body.crop not in [p[0] for p in PROFILES]:
        raise HTTPException(422, "없는 작물입니다.")
    return dict(ok=sim.plant(index, body.crop))


@protected.post("/sections/{index}/harvest")
async def harvest(index: int = Depends(section_index)):
    return dict(ok=sim.harvest(index))


@protected.post("/sections/{index}/plow")
async def plow(index: int = Depends(section_index)):
    return dict(ok=sim.plow(index))


@protected.post("/sections/{index}/pests")
async def pests(index: int = Depends(section_index)):
    return dict(ok=sim.inject_pests(index))


@protected.post("/harvest-all")
async def harvest_all():
    return dict(count=sim.harvest_all())


# ---------- 장치 수동 제어 ----------
class DeviceBody(BaseModel):
    mode: str       # auto / on / off


@protected.post("/sections/{index}/devices/{key}")
async def device_mode(key: str, body: DeviceBody, index: int = Depends(section_index)):
    try:
        return dict(changed=sim.set_device_mode(index, key, body.mode))
    except KeyError:
        raise HTTPException(404, "없는 장치입니다.")
    except ValueError as e:
        raise HTTPException(422, str(e))


@protected.post("/sections/{index}/devices/{key}/dose")
async def device_dose(key: str, index: int = Depends(section_index)):
    try:
        return dict(ok=sim.dose(index, key))
    except KeyError:
        raise HTTPException(404, "없는 장치입니다.")
    except ValueError as e:
        raise HTTPException(422, str(e))


# ---------- 작물 적정 조건 ----------
class CropBody(BaseModel):
    temperature: tuple[float, float] | None = None
    humidity: tuple[float, float] | None = None
    soil: tuple[float, float] | None = None
    nutrient: tuple[float, float] | None = None
    co2: tuple[float, float] | None = None
    luminosity: float | None = None     # 최소 조도 하나


def crop_name(name: str) -> str:
    if name not in CROPS:
        raise HTTPException(404, "없는 작물입니다.")
    return name


@protected.put("/crops/{name}")
async def update_crop(body: CropBody, name: str = Depends(crop_name)):
    try:
        sim.update_profile(name, body.model_dump(exclude_none=True))
    except ValueError as e:
        raise HTTPException(422, str(e))
    return dict(ok=True)


@protected.delete("/crops/{name}")
async def reset_crop(name: str = Depends(crop_name)):
    sim.reset_profile(name)
    return dict(ok=True)


# ---------- 시뮬레이터 ----------
class SimBody(BaseModel):
    running: bool | None = None
    speed: int | None = None
    weather: int | None = None
    season: str | None = None
    autoReplant: bool | None = None


@protected.patch("/sim")
async def update_sim(body: SimBody):
    if body.weather is not None:
        if body.weather not in [d for _, d in WEATHER]:
            raise HTTPException(422, "없는 날씨입니다.")
        sim.set_weather(body.weather)
    if body.season is not None:
        if body.season not in dict(SEASONS):
            raise HTTPException(422, "없는 계절입니다.")
        sim.set_season(body.season)
    if body.running is not None:
        sim.set_running(body.running)
    if body.speed is not None:
        sim.set_speed(body.speed)
    if body.autoReplant is not None:
        sim.set_auto_replant(body.autoReplant)
    return dict(ok=True)


@protected.post("/sim/step")
async def step():
    sim.step()
    return dict(ok=True)


@protected.post("/sim/reset")
async def reset():
    sim.reset()
    return dict(ok=True)


app.include_router(protected)


# ---------- 실시간 상태 ----------
@app.websocket("/api/ws")
async def stream(ws: WebSocket, token: str = ""):
    if token not in sessions:
        await ws.close(code=4401)
        return
    await ws.accept()
    closed = asyncio.Event()

    async def watch_close():
        """화면이 보내는 것은 없지만, 연결이 끊긴 걸 알아야 정지 중에도 기다림을 끝낼 수 있다."""
        try:
            while (await ws.receive())["type"] != "websocket.disconnect":
                pass
        finally:
            closed.set()

    watcher = asyncio.create_task(watch_close())
    cursor = {}
    try:
        while not closed.is_set():
            changed = sim.changed           # 보내기 전에 받아 둬야 보내는 동안의 변경을 놓치지 않는다
            msg, cursor = sim.sync(cursor)
            await ws.send_json(msg)
            await asyncio.sleep(SEND_INTERVAL)
            if token not in sessions:
                await ws.close(code=4401)
                return
            waits = [asyncio.create_task(changed.wait()), asyncio.create_task(closed.wait())]
            _, pending = await asyncio.wait(waits, return_when=asyncio.FIRST_COMPLETED)
            for t in pending:
                t.cancel()
    except (WebSocketDisconnect, RuntimeError):
        pass                                # 보내는 도중에 끊긴 경우
    finally:
        watcher.cancel()


# 빌드된 웹 화면 (npm run build 후). API 경로보다 뒤에 붙여야 /api가 가려지지 않는다.
if WEB_DIST.is_dir():
    app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="web")
