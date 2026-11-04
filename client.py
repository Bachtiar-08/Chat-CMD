import asyncio
import json
import os
import websockets

SERVER = "wss://chat-domain-kamu.onrender.com"
TOKEN = os.environ["CHATCMD_TOKEN"]

async def main():
    name = input("Nama kamu: ").strip()[:30]

    try:
        async with websockets.connect(
            SERVER,
            max_size=4096
        ) as ws:

            await ws.send(json.dumps({
                "token": TOKEN
            }))

            response = json.loads(await ws.recv())

            if response.get("type") != "ready":
                print("Gagal terhubung.")
                return

            print("\n=== CHATCMD AKTIF ===")
            print("Ketik /quit untuk keluar.")

            async def receive():
                async for raw in ws:
                    data = json.loads(raw)
                    if data.get("type") == "message":
                        print(
                            f"\n[{data['sender']}] "
                            f"{data['text']}"
                        )

            task = asyncio.create_task(receive())

            try:
                while True:
                    msg = await asyncio.to_thread(
                        input, "> "
                    )

                    if msg == "/quit":
                        break

                    if msg.strip():
                        await ws.send(json.dumps({
                            "type": "message",
                            "sender": name,
                            "text": msg[:1000]
                        }))
            finally:
                task.cancel()

    except Exception as e:
        print("Kesalahan:", e)

asyncio.run(main())