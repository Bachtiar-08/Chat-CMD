import os
import asyncio
import websockets

TOKEN = os.environ.get("CHATCMD_TOKEN", "")
PORT = int(os.environ.get("PORT", 8765))
MAX_USERS = 2

clients = {}  # ws -> nama


async def broadcast(message, sender=None):
    for ws in list(clients):
        if ws is not sender:
            try:
                await ws.send(message)
            except Exception:
                pass


async def handler(ws):
    try:
        token = await asyncio.wait_for(ws.recv(), timeout=10)
    except Exception:
        return

    if TOKEN and token != TOKEN:
        await ws.send("[server] Token salah.")
        await ws.close(code=4001, reason="unauthorized")
        return

    if len(clients) >= MAX_USERS:
        await ws.send("[server] Server penuh (maks 2 pengguna).")
        await ws.close(code=4002, reason="full")
        return

    try:
        name = (await asyncio.wait_for(ws.recv(), timeout=10)).strip()[:20]
    except Exception:
        return
    if not name:
        name = "Anonim"
    if name in clients.values():
        name += "2"

    clients[ws] = name
    await ws.send(f"[server] Terhubung sebagai {name}. Ketik /quit untuk keluar.")
    await broadcast(f"[server] {name} bergabung.", sender=ws)

    try:
        async for message in ws:
            await broadcast(f"{name}: {message}", sender=ws)
    except websockets.ConnectionClosed:
        pass
    finally:
        clients.pop(ws, None)
        await broadcast(f"[server] {name} keluar.")


async def main():
    async with websockets.serve(handler, "0.0.0.0", PORT):
        print(f"Server jalan di port {PORT}", flush=True)
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())