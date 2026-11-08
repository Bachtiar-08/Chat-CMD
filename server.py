import asyncio
import os
from datetime import datetime

import websockets

TOKEN = os.environ.get("CHATCMD_TOKEN", "")
PORT = int(os.environ.get("PORT", 8765))
MAX_USERS = 10
TYPING = "\x01typing"

clients = {}  # websocket -> username

HELP = (
    "[server] Perintah tersedia:\n"
    "  /users            melihat pengguna online\n"
    "  /pm nama pesan    mengirim pesan pribadi\n"
    "  /help             menampilkan bantuan\n"
    "  /clear            membersihkan terminal (di sisi client)\n"
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
                await send_safe(other, stamped(f"[PM dari {name}] {msg}"))
                await send_safe(ws, stamped(f"[PM ke {other_name}] {msg}"))
                return
        await send_safe(ws, stamped(f"[server] {target} tidak ditemukan."))

    elif cmd == "/quit":
        await send_safe(ws, stamped("[server] Sampai jumpa!"))
        await ws.close(code=1000, reason="user quit")

    else:
        await send_safe(ws, "[server] Perintah tidak dikenal. Ketik /help")


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

        if len(clients) >= MAX_USERS:
            await send_safe(ws, f"[server] Server penuh (maks {MAX_USERS} pengguna).")
            await ws.close(code=4002, reason="full")
            return

        try: