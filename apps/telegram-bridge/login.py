"""Interactive Telegram login supporting both QR Code scanning and Phone Number verification."""
import asyncio
import base64
import os
import sys
import time
import qrcode

from dotenv import load_dotenv
from pyrogram import Client, raw
from pyrogram.errors import (
    SessionPasswordNeeded,
    PhoneCodeInvalid,
    PhoneCodeExpired,
    FloodWait,
    PhoneNumberInvalid,
    AuthTokenAlreadyAccepted,
    AuthTokenExpired,
)
from pyrogram.raw.functions.auth import ExportLoginToken, ImportLoginToken
from pyrogram.raw.types.auth import LoginToken, LoginTokenSuccess, LoginTokenMigrateTo

from config import ROOT


async def qr_code_login(app: Client, api_id: int, api_hash: str) -> str:
    print("\nRequesting QR login token from Telegram DataCenter 5...")
    res = await app.invoke(ExportLoginToken(api_id=api_id, api_hash=api_hash, except_ids=[]))

    if not isinstance(res, LoginToken):
        raise RuntimeError(f"Unexpected Telegram response: {type(res).__name__}")

    token_b64 = base64.urlsafe_b64encode(res.token).decode("utf-8").rstrip("=")
    qr_url = f"tg://login?token={token_b64}"

    print("\n" + "=" * 65)
    print(">> SCAN THIS QR CODE WITH YOUR OFFICIAL TELEGRAM MOBILE APP <<")
    print("1. Open Telegram on your phone.")
    print("2. Go to: Settings  ->  Devices  ->  'Link Desktop Device'")
    print("3. Point your camera at the QR code below:")
    print("=" * 65 + "\n")

    sys.stdout.reconfigure(encoding="utf-8")
    qr = qrcode.QRCode()
    qr.add_data(qr_url)
    qr.print_ascii(invert=True)

    print("\n" + "=" * 65)
    print("Waiting for you to scan and tap 'Link Device' on your phone...")
    print("=" * 65 + "\n")

    while True:
        await asyncio.sleep(1.5)
        try:
            res = await app.invoke(ExportLoginToken(api_id=api_id, api_hash=api_hash, except_ids=[]))
            if isinstance(res, LoginTokenSuccess):
                user = res.authorization.user
                await app.storage.user_id(user.id)
                await app.storage.is_bot(False)
                print(f"\n[OK] Authenticated successfully as: {getattr(user, 'first_name', 'Telegram User')} (ID: {user.id})")
                return await app.export_session_string()
        except AuthTokenAlreadyAccepted:
            # Phone confirmed the link!
            print("\n[OK] Scan detected! Finalizing authentication...")
            try:
                me = await app.get_me()
                await app.storage.user_id(me.id)
                await app.storage.is_bot(False)
                print(f"[OK] Authenticated successfully as: {getattr(me, 'first_name', 'Telegram User')} (ID: {me.id})")
                return await app.export_session_string()
            except SessionPasswordNeeded:
                pwd = input("\nTwo-Step Verification (2FA Cloud Password) is enabled. Enter password: ").strip()
                await app.check_password(pwd)
                me = await app.get_me()
                await app.storage.user_id(me.id)
                await app.storage.is_bot(False)
                return await app.export_session_string()
        except AuthTokenExpired:
            # Regenerate expired token
            print("\nQR code expired. Generating fresh QR code...")
            res = await app.invoke(ExportLoginToken(api_id=api_id, api_hash=api_hash, except_ids=[]))
            if isinstance(res, LoginToken):
                token_b64 = base64.urlsafe_b64encode(res.token).decode("utf-8").rstrip("=")
                qr_url = f"tg://login?token={token_b64}"
                qr = qrcode.QRCode()
                qr.add_data(qr_url)
                qr.print_ascii(invert=True)
        except SessionPasswordNeeded:
            pwd = input("\nTwo-Step Verification (2FA Cloud Password) is enabled. Enter password: ").strip()
            await app.check_password(pwd)
            try:
                me = await app.get_me()
                await app.storage.user_id(me.id)
                await app.storage.is_bot(False)
                print(f"[OK] Authenticated as: {getattr(me, 'first_name', 'Telegram User')} (ID: {me.id})")
            except Exception:
                pass
            return await app.export_session_string()
        except Exception as e:
            # Check if session is already authorized regardless
            try:
                me = await app.get_me()
                if me and me.id:
                    await app.storage.user_id(me.id)
                    await app.storage.is_bot(False)
                    print(f"\n[OK] Authenticated as: {getattr(me, 'first_name', 'Telegram User')} (ID: {me.id})")
                    return await app.export_session_string()
            except Exception:
                pass


async def phone_code_login(app: Client) -> str:
    phone_number = input("\nEnter your phone number with country code (e.g. +919876543210): ").strip()
    if not phone_number.startswith("+"):
        phone_number = "+" + phone_number

    print(f"\nRequesting login code from Telegram for {phone_number}...")
    try:
        sent_code = await app.send_code(phone_number)
    except PhoneNumberInvalid:
        print(f"\n[ERROR] Telegram says '{phone_number}' is an invalid phone number.")
        sys.exit(1)
    except FloodWait as e:
        print(f"\n[RATE LIMIT] Telegram says you must wait {e.value} seconds.")
        sys.exit(1)

    code_hash = sent_code.phone_code_hash
    delivery_type = str(getattr(sent_code, "type", "APP")).upper()
    print(f"\n>> Code sent via: {delivery_type} (Check official 'Telegram' chat in app) <<\n")

    code_input = input("Enter the 5-digit code: ").strip()
    try:
        await app.sign_in(phone_number, code_hash, code_input)
    except SessionPasswordNeeded:
        pwd = input("Enter your Telegram 2FA cloud password: ").strip()
        await app.check_password(pwd)
    except (PhoneCodeInvalid, PhoneCodeExpired) as e:
        print(f"\n[ERROR] Invalid or expired code: {type(e).__name__}")
        sys.exit(1)

    return await app.export_session_string()


async def main():
    load_dotenv(ROOT / ".env")
    for key in ["TELEGRAM_API_ID", "TELEGRAM_API_HASH"]:
        if not os.environ.get(key):
            raise ValueError(f"Set {key} in apps/telegram-bridge/.env first")

    api_id = int(os.environ["TELEGRAM_API_ID"])
    api_hash = os.environ["TELEGRAM_API_HASH"].strip()

    print("Connecting to Telegram...")
    app = Client("onfloor", api_id=api_id, api_hash=api_hash, in_memory=True, ipv6=False)
    # Direct connection to DataCenter 5 (Asia/Singapore) where your account is hosted
    await app.storage.open()
    await app.storage.dc_id(5)
    await app.connect()
    print("Connected to Telegram DataCenter 5 successfully.")

    print("\n" + "=" * 50)
    print("  TELEGRAM AUTHENTICATION")
    print("=" * 50)
    print("[1] QR Code (Recommended: Instant scan via phone camera, no SMS/code)")
    print("[2] Phone number & confirmation code")
    choice = input("\nSelect login method [1 or 2, default 1]: ").strip()

    if choice == "2":
        session = await phone_code_login(app)
    else:
        session = await qr_code_login(app, api_id, api_hash)

    await app.disconnect()

    path = ROOT / ".env"
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    lines = [line for line in lines if not line.startswith("TELEGRAM_SESSION_STRING=")]
    lines.append("TELEGRAM_SESSION_STRING=" + session)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if os.name != "nt":
        path.chmod(0o600)

    print("\n" + "*" * 65)
    print("SUCCESS! Telegram session string generated and saved to .env")
    print("You can now start the bridge with: python bridge.py")
    print("*" * 65)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nLogin cancelled.")
    except Exception as error:
        print(f"\nLogin failed ({type(error).__name__}: {error}). Check your credentials.")
        sys.exit(1)
