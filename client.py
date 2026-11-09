
import os
import time
import asyncio
import websockets

from pyfiglet import Figlet
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.styles import Style

# Server lokal untuk pengujian
SERVER = "ws://127.0.0.1:8765"

TOKEN = os.environ.get("CHATCMD_TOKEN", "")
TYPING = "\x01typing"

typing_users = {}

BLUE = "\033[96m"
RESET = "\033[0m"


def print_banner():
    fig = Figlet(font="big")
    logo = fig.renderText("CHATCMD")

    print(BLUE + logo + RESET)
    print(BLUE + "       REAL-TIME TERMINAL CHAT" + RESET)
    print("       Ketik /help untuk melihat perintah.\n")


def toolbar():
    now = time.time()

    # Hapus pengguna yang masa indikatornya sudah habis
    expired = [
        name for name, expiry in typing_users.items()
        if expiry <= now
    ]

    for name in expired:
        typing_users.pop(name, None)

    names = list(typing_users.keys())

    if names:
        return " " + ", ".join(names) + " sedang mengetik..."

    return " CHATCMD | /help untuk bantuan"


def remove_typing_status(message):
    # Pesan server berbentuk [HH:MM:SS] nama: pesan
    if "] " not in message or ": " not in message:
        return

    try:
        content = message.split("] ", 1)[1]
        sender = content.split(": ", 1)[0]
        typing_users.pop(sender, None)
    except (IndexError, ValueError):
        pass


async def receiver(ws, session):
    try:
        async for msg in ws:
            if msg.startswith(TYPING + ":"):
                username = msg.split(":", 1)[1]
                typing_users[username] = time.time() + 3

            else:
                remove_typing_status(msg)
                print(msg)

    except websockets.ConnectionClosed:
        pass

    finally:
        print("\n[Koneksi terputus]")

        try:
            session.app.exit(exception=EOFError)
        except Exception:
            pass


async def main():
    name = input("Nama kamu: ").strip()[:20]

    if not name:
        name = "Anonim"

    print_banner()

    try:
        async with websockets.connect(
            SERVER,
            open_timeout=30,
            ping_interval=20,
            max_size=4096,
        ) as ws:

            await ws.send(TOKEN)
            await ws.send(name)

            session = PromptSession(
                bottom_toolbar=toolbar,
                refresh_interval=0.5,
                style=Style.from_dict({
                    "bottom-toolbar": "noreverse",
                }),
            )

            last_sent = 0

            def on_change(buffer):
                nonlocal last_sent

                now = time.time()

                if (
                    buffer.text
                    and not buffer.text.startswith("/")
                    and now - last_sent > 2
                ):
                    last_sent = now
                    asyncio.create_task(ws.send(TYPING))

            session.default_buffer.on_text_changed += on_change

            task = asyncio.create_task(receiver(ws, session))

            try:
                with patch_stdout():
                    while True:
                        try:
                            text = await session.prompt_async("> ")

                        except (EOFError, KeyboardInterrupt):
                            break

                        text = text.strip()

                        if not text:
                            continue

                        if text == "/clear":
                            os.system(
                                "cls" if os.name == "nt" else "clear"
                            )
                            print_banner()
                            continue

                        if text == "/quit":
                            await ws.send("/quit")
                            break

                        await ws.send(text)

            finally:
                task.cancel()
                await asyncio.gather(
                    task,
                    return_exceptions=True
                )

    except Exception as e:
        print(f"\nGagal konek: {e}")


if __name__ == "__main__":
    asyncio.run(main())
