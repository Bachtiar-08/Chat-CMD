import os
import asyncio
import websockets
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout

SERVER = "wss://web-production-7dc24.up.railway.app"
TOKEN = os.environ.get("CHATCMD_TOKEN", "")


async def receiver(ws, session):
    try:
        async for msg in ws:
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
        session = PromptSession()
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