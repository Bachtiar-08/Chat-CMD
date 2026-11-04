import asyncio
import json
import os
import websockets

TOKEN = os.environ["CHATCMD_TOKEN"]
PORT = int(os.environ.get("PORT", 10000))
CLIENTS = set()

async def handler(ws):
    try:
        auth = json.loads(await asyncio.wait_for(ws.recv(), 10))

        if auth.get("token") != TOKEN:
            await ws.close(code=1008)
            return

        if len(CLIENTS) >= 2:
            await ws.close(code=1013)
            return

        CLIENTS.add(ws)
        await ws.send(json.dumps({"type": "ready"}))

        async for raw in ws:
            data = json.loads(raw)

            if data.get("type") != "message":
                continue

            message = str(data.get("text", ""))[:1000]

            if not message.strip():
                continue

            outgoing = json.dumps({
                "type": "message",
                "sender": str(data.get("sender", "User"))[:30],
                "text": message
            })

            for client in list(CLIENTS):
                if client != ws:
                    await client.send(outgoing)

    except (asyncio.TimeoutError, ValueError):
        await ws.close()
    except websockets.ConnectionClosed:
        pass
    finally:
        CLIENTS.discard(ws)

async def main():
    print(f"ChatCMD berjalan pada port {PORT}")

    async with websockets.serve(
        handler,
        "0.0.0.0",
        PORT,
        max_size=4096,
        ping_interval=20,
        ping_timeout=20
    ):
        await asyncio.Future()

asyncio.run(main())