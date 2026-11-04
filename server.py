import os
import asyncio
import websockets

TOKEN = os.environ.get("CHATCMD_TOKEN", "")
PORT = int(os.environ.get("PORT", 8765))
MAX_USERS = 10

clients = {}  # ws -> nama

HELP = (
    "[server] Perintah:\n"
    "  /users            daftar yang online\n"
    "  /pm nama pesan    pesan pribadi\n"
    "  /help             bantuan ini\n"
    "  /quit             keluar"
)


async def broadcast(message, sender=None):
    for ws in list(clients):
        if ws is not sender:
            try:
                await ws.send(message)
            except Exception:
                pass


async def handle_command(ws, name, text):
    parts = text.split(maxsplit=2)
    cmd = parts[0].lower()

    if cmd == "/users":
        await ws.send("[server] Online: " + ", ".join(clients.values()))
    elif cmd == "/help":
        await ws.send(HELP)
    elif cmd == "/pm":
        if len(parts) < 3:
            await ws.send("[server] Format: /pm nama pesan")
            return
        target, msg = parts[1], parts[2]
        for other, other_name in clients.items():
            if other_name.lower() == target.lower():
                await other.send(f"[PM dari {name}] {msg}")
                await ws.send(f"[PM ke {other_name}] {msg}")
                return
        await ws.send(f"[server] {target} tidak ditemukan.")
    else:
        await ws.send("[server] Perintah tidak dikenal. Ketik /help")


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
        await ws.send(f"[server] Server penuh (maks {MAX_USERS} pengguna).")
        await ws.close(code=4002, reason="full")
        return

    try:
        name = (await asyncio.wait_for(ws.recv(), timeout=10)).strip()[:20]
    except Exception:
        return
    name = name.replace(" ", "_") or "Anonim"
    while name in clients.values():
        name += "2"

    clients[ws] = name
    await ws.send(f"[server] Terhubung sebagai {name}. Ketik /help untuk perintah.")
    await broadcast(f"[server] {name} bergabung.", sender=ws)

    try:
        async for message in ws:
            if message.startswith("/"):
                await handle_command(ws, name, message)
            else:
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