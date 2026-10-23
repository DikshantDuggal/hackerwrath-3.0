"""Robust Telegram QR login using Telethon engine and exporting to Pyrogram session string."""
import asyncio
import base64
import os
import struct
import sys
import qrcode
from pathlib import Path
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

ROOT = Path(__file__).resolve().parent


def export_pyrogram_session(client: TelegramClient, user_id: int) -> str:
    # Pyrogram SESSION_STRING_FORMAT = ">BI?256sQ?"
    dc_id = client.session.dc_id
    api_id = client.api_id
    test_mode = False
    auth_key = client.session.auth_key.key
    is_bot = False
    packed = struct.pack(">BI?256sQ?", dc_id, api_id, test_mode, auth_key, user_id, is_bot)
    return base64.urlsafe_b64encode(packed).decode().rstrip("=")


async def main():
    load_dotenv(ROOT / ".env")
    for key in ["TELEGRAM_API_ID", "TELEGRAM_API_HASH"]:
        if not os.environ.get(key):
            raise ValueError(f"Set {key} in apps/telegram-bridge/.env first")

    api_id = int(os.environ["TELEGRAM_API_ID"])
    api_hash = os.environ["TELEGRAM_API_HASH"].strip()

    print("Initializing Telegram QR engine...")
    sys.stdout.reconfigure(encoding="utf-8")

    client = TelegramClient(None, api_id, api_hash)
    await client.connect()

    while True:
        print("\nRequesting fresh QR login token from Telegram...")
        qr_login = await client.qr_login()

        print("\n" + "=" * 65)
        print(">> SCAN THIS QR CODE WITH YOUR OFFICIAL TELEGRAM MOBILE APP <<")
        print("1. Open Telegram on your phone.")
        print("2. Go to: Settings  ->  Devices  ->  'Link Desktop Device'")
        print("3. Point your camera at the QR code below:")
        print("=" * 65 + "\n")

        qr = qrcode.QRCode()
        qr.add_data(qr_login.url)
        qr.print_ascii(invert=True)

        print("\n" + "=" * 65)
        print("Waiting for scan on your phone... (Scan now)")
        print("=" * 65 + "\n")

        try:
            user = await qr_login.wait(timeout=35)
            print(f"\n[SUCCESS!] Authenticated as: {getattr(user, 'first_name', 'Telegram User')} (ID: {user.id})")
            session_string = export_pyrogram_session(client, user.id)
            break
        except asyncio.TimeoutError:
            print("\nQR code expired. Refreshing QR code...")
            continue
        except SessionPasswordNeededError:
            pwd = input("\nTwo-Step Verification (2FA Cloud Password) is enabled. Enter password: ").strip()
            user = await client.sign_in(password=pwd)
            print(f"\n[SUCCESS!] Authenticated with 2FA as: {getattr(user, 'first_name', 'Telegram User')} (ID: {user.id})")
            session_string = export_pyrogram_session(client, user.id)
            break

    await client.disconnect()

    path = ROOT / ".env"
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    lines = [line for line in lines if not line.startswith("TELEGRAM_SESSION_STRING=")]
    lines.append("TELEGRAM_SESSION_STRING=" + session_string)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\n" + "*" * 65)
    print("SUCCESS! Telegram session string saved to .env")
    print("You can now start the bridge with: python bridge.py")
    print("*" * 65)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nLogin cancelled.")
    except Exception as e:
        print(f"\nError: {type(e).__name__} ({e})")
        sys.exit(1)
