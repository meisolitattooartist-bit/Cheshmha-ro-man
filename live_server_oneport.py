import asyncio
import json
import os
import random
import secrets
from datetime import datetime
from pathlib import Path

from aiohttp import web

rooms = {}

def now():
    return datetime.now().astimezone().isoformat()

def public_state(room_id, role="viewer"):
    room = rooms[room_id]
    return {
        "type": "state",
        "room_id": room_id,
        "role": role,
        "title": room["title"],
        "sponsor": room["sponsor"],
        "prize": room["prize"],
        "winner_count": room["winner_count"],
        "participants": room["participants"],
        "started": room["started"],
        "winners": room["winners"],
    }

async def handler(request):
    ws = web.WebSocketResponse(heartbeat=30)
    await ws.prepare(request)

    room_id = None
    role = "viewer"

    try:
        async for msg in ws:
            if msg.type != web.WSMsgType.TEXT:
                continue

            data = json.loads(msg.data)
            action = data.get("action")

            if action == "create":
                requested = str(data.get("room_id", "")).strip()
                room_id = requested or "CR-" + secrets.token_hex(3).upper()

                if room_id in rooms:
                    await ws.send_json({"type":"error","message":"این اتاق قبلاً وجود دارد"})
                    continue

                token = secrets.token_urlsafe(32)

                rooms[room_id] = {
                    "host_token": token,
                    "title": str(data.get("title","")).strip(),
                    "sponsor": str(data.get("sponsor","")).strip(),
                    "prize": str(data.get("prize","")).strip(),
                    "winner_count": max(1, int(data.get("winner_count",1))),
                    "participants": [],
                    "started": False,
                    "winners": [],
                    "clients": set()
                }

                role = "host"
                rooms[room_id]["clients"].add(ws)

                state = public_state(room_id, role)
                state["host_token"] = token
                await ws.send_json(state)
                print(f"🏠 CREATE | {room_id} | HOST", flush=True)
                continue

            if action == "join":
                requested = str(data.get("room_id","")).strip()
                room = rooms.get(requested)

                if not room:
                    await ws.send_json({"type":"error","message":"این اتاق وجود ندارد یا هنوز ساخته نشده است"})
                    continue

                room_id = requested
                supplied = str(data.get("host_token","")).strip()

                role = "host" if supplied and secrets.compare_digest(supplied, room["host_token"]) else "viewer"
                room["clients"].add(ws)

                await ws.send_json(public_state(room_id, role))
                print(f"🔗 JOIN | {room_id} | {role.upper()} | Users: {len(room['clients'])}", flush=True)
                continue

            if not room_id or room_id not in rooms:
                await ws.send_json({"type":"error","message":"ابتدا وارد اتاق شوید"})
                continue

            room = rooms[room_id]

            if action == "participants":
                if role != "host":
                    await ws.send_json({"type":"error","message":"فقط سازنده اتاق می‌تواند اسامی را تغییر دهد"})
                    continue

                if room["started"]:
                    await ws.send_json({"type":"error","message":"قرعه‌کشی شروع شده و لیست قفل است"})
                    continue

                clean = []
                for name in data.get("participants", []):
                    name = " ".join(str(name).split())
                    if name and name not in clean:
                        clean.append(name)

                room["participants"] = clean

                for client in list(room["clients"]):
                    try:
                        await client.send_json({"type":"participants","participants":clean})
                    except Exception:
                        room["clients"].discard(client)
                continue

            if action == "start":
                if role != "host":
                    await ws.send_json({"type":"error","message":"فقط سازنده اتاق می‌تواند قرعه‌کشی را شروع کند"})
                    continue

                if not room["participants"]:
                    await ws.send_json({"type":"error","message":"حداقل یک شرکت‌کننده لازم است"})
                    continue

                room["started"] = True

                for client in list(room["clients"]):
                    try:
                        await client.send_json({"type":"start"})
                    except Exception:
                        room["clients"].discard(client)

                print(f"🔒 START | {room_id}", flush=True)
                continue

            if action == "spin":
                if role != "host" or not room["started"]:
                    continue

                if len(room["winners"]) >= room["winner_count"]:
                    continue

                used = {w["index"] for w in room["winners"]}
                available = [i for i in range(len(room["participants"])) if i not in used]

                if not available:
                    continue

                index = random.choice(available)
                winner = {
                    "index": index,
                    "name": room["participants"][index],
                    "time": now()
                }
                room["winners"].append(winner)

                payload = {
                    "type":"spin",
                    "index":index,
                    "name":winner["name"],
                    "extra_turns":random.randint(5,7),
                    "winners":room["winners"]
                }

                for client in list(room["clients"]):
                    try:
                        await client.send_json(payload)
                    except Exception:
                        room["clients"].discard(client)

                print(f"🎯 SPIN | {room_id} | {winner['name']}", flush=True)

    finally:
        if room_id in rooms:
            rooms[room_id]["clients"].discard(ws)

    return ws

async def main():
    app = web.Application()
    app.router.add_get("/ws", handler)
    app.router.add_get("/", lambda request: web.HTTPFound("/index.html"))

    static_dir = Path(__file__).parent / "static"
    app.router.add_static("/", static_dir, show_index=True)

    port = int(os.environ.get("PORT", "8080"))
    print("👁️ چشم‌ها رو من | One-Port Live Server")
    print(f"📡 HTTP + WebSocket | Port {port}")
    print("🔒 Host / Viewer System: ON")

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    await asyncio.Future()

asyncio.run(main())
