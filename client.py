import os
import time
import asyncio
import websockets
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.styles import Style

SERVER = "wss://web-production-7dc24.up.railway.app"
TOKEN = os.environ.get("CHATCMD_TOKEN", "")
TYPING = "\x01typing"

typing_users = {}  # nama -> waktu kedaluwarsa


def toolbar():
    now = time.time()
    names = [n for n, t in typing_users.items() if t > now]
    if names:
        return " " + ", ".join(names) + " sedang mengetik..."
    return " "


async def receiver(ws, session):
    try:
        async for msg in ws:
            if msg.startswith(TYPING + ":"):
                typing_users[msg.split(":", 1)[1]] = time.time() + 3
            else:
                if ": " in msg:
                    typing_users.pop(msg.split(": ", 1)[0], None)
                print(msg)
    except websockets.ConnectionClosed:
        pass
    print("[Koneksi terputus]")
    try:
        session.app.exit(exception=EOFError)
    except Exception:
        pass


async def main(name):
    async with websockets.connect(SERVER, open_timeout=30, ping_interval=20) as ws:
        await ws.send(TOKEN)
        await ws.send(name)

        session = PromptSession(
            bottom_toolbar=toolbar,
            refresh_interval=0.5,
            style=Style.from_dict({"bottom-toolbar": "noreverse"}),
        )

        last_sent = 0

        def on_change(buf):
            nonlocal last_sent
            now = time.time()
            if buf.text and not buf.text.startswith("/") and now - last_sent > 2:
                last_sent = now
                asyncio.ensure_future(ws.send(TYPING))

        session.default_buffer.on_text_changed += on_change

        task = asyncio.create_task(receiver(ws, session))
        with patch_stdout():
            while True:
                try:
                    text = await session.prompt_async("> ")
                except (EOFError, KeyboardInterrupt):
                    break
                text = text.strip()
                if text == "/quit":
                    break
                if text:
                    await ws.send(text)
        task.cancel()


name = input("Nama kamu: ").strip()
try:
    asyncio.run(main(name))
except Exception as e:
    print(f"Gagal konek: {e}")