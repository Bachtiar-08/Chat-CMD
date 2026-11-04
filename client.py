import os
import asyncio
import websockets

SERVER = "wss://web-production-7dc24.up.railway.app"
TOKEN = os.environ.get("CHATCMD_TOKEN", "")


async def receiver(ws):
    try:
        async for msg in ws:
            print("\r" + msg + "\n> ", end="", flush=True)
    except websockets.ConnectionClosed:
        print("\n[Koneksi terputus]")
        os._exit(0)


async def main():
    async with websockets.connect(SERVER, open_timeout=30, ping_interval=20) as ws:
        await ws.send(TOKEN)
        task = asyncio.create_task(receiver(ws))
        while True:
            text = await asyncio.to_thread(input, "> ")
            if text.strip() == "/quit":
                break
            if text.strip():
                await ws.send(text)
        task.cancel()


try:
    asyncio.run(main())
except Exception as e:
    print(f"Gagal konek: {e}")