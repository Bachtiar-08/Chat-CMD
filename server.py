
import asyncio
import os
from datetime import datetime

import websockets

TOKEN = os.environ.get("CHATCMD_TOKEN", "")
PORT = int(os.environ.get("PORT", 8765))
MAX_USERS = 10
TYPING = "\x01typing"

clients = {}

HELP = (
    "[server] Perintah tersedia:\n"
    "  /users            melihat pengguna online\n"
    "  /pm nama pesan    mengirim pesan pribadi\n"
    "  /help             menampilkan bantuan\n"
    "  /clear            membersihkan terminal\n"
    "  /quit             keluar dari chat"
)


def timestamp():
    return datetime.now().strftime("[%H:%M:%S]")


def stamped(message):
    return f"{timestamp()} {message}"


async def send_safe(ws, message):
    try:
        await ws.send(message)
        return True
    except websockets.ConnectionClosed:
        return False


async def broadcast(message, sender=None):
    for ws in list(clients):
        if ws is not sender:
            await send_safe(ws, message)


async def handle_command(ws, name, text):
    parts = text.split(maxsplit=2)
    cmd = parts[0].lower()

    if cmd == "/users":
        online = ", ".join(clients.values()) or "Belum ada pengguna."
        await send_safe(ws, stamped("[server] Online: " + online))

    elif cmd == "/help":
        await send_safe(ws, HELP)

    elif cmd == "/pm":
        if len(parts) < 3:
            await send_safe(ws, "[server] Format: /pm nama pesan")
            return

        target, msg = parts[1], parts[2]

        for other, other_name in list(clients.items()):
            if other_name.lower() == target.lower():
                await send_safe(
                    other,
                    stamped(f"[PM dari {name}] {msg}")
                )
                await send_safe(
                    ws,
                    stamped(f"[PM ke {other_name}] {msg}")
                )
                return

        await send_safe(
            ws,
            stamped(f"[server] {target} tidak ditemukan.")
        )

    elif cmd == "/quit":
        await send_safe(ws, stamped("[server] Sampai jumpa!"))
        await ws.close(code=1000, reason="user quit")

    else:
        await send_safe(
            ws,
            "[server] Perintah tidak dikenal. Ketik /help"
        )


async def handler(ws):
    name = None

    try:
        try:
            token = await asyncio.wait_for(ws.recv(), timeout=10)
        except (asyncio.TimeoutError, websockets.ConnectionClosed):
            return

        if TOKEN and token != TOKEN:
            await send_safe(ws, "[server] Token salah.")
            await ws.close(code=4001, reason="unauthorized")
            return

        try:
            name = (
                await asyncio.wait_for(ws.recv(), timeout=10)
            ).strip()[:20]
        except (asyncio.TimeoutError, websockets.ConnectionClosed):
            return

        name = name.replace(" ", "_") or "Anonim"

        if len(clients) >= MAX_USERS:
            await send_safe(
                ws,
                f"[server] Server penuh (maks {MAX_USERS} pengguna)."
            )
            await ws.close(code=4002, reason="full")
            return

        while name in clients.values():
            name += "2"

        clients[ws] = name

        await send_safe(
            ws,
            stamped(f"[server] Terhubung sebagai {name}. Ketik /help.")
        )

        await broadcast(
            stamped(f"[SYSTEM] {name} telah bergabung."),
            sender=ws
        )

        async for message in ws:
            if message == TYPING:
                await broadcast(
                    f"{TYPING}:{name}",
                    sender=ws
                )

            elif message.startswith("/"):
                await handle_command(ws, name, message)

            elif message.strip():
                await broadcast(
                    stamped(f"{name}: {message}"),
                    sender=ws
                )

    except websockets.ConnectionClosed:
        pass

    finally:
        if ws in clients:
            clients.pop(ws, None)
            await broadcast(
                stamped(f"[SYSTEM] {name} telah keluar.")
            )


async def main():
    print(f"ChatCMD server berjalan pada port {PORT}", flush=True)

    async with websockets.serve(
        handler,
        "0.0.0.0",
        PORT,
        max_size=4096,
        ping_interval=20,
        ping_timeout=20
    ):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
