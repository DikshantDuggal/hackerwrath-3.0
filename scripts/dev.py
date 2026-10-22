"""Run API, contract generation and optional Android continuous builds as one group."""
import argparse
import os
import signal
import subprocess
import sys
import time

from watchfiles import watch

from contracts import ROOT, generate


def watch_contracts() -> None:
    for _ in watch(ROOT / "packages/contracts/src", watch_filter=lambda _, p: p.endswith(".py")):
        # A fresh process avoids using cached Python model imports after edits.
        subprocess.run([sys.executable, "scripts/contracts.py"], cwd=ROOT, check=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--android", action="store_true")
    parser.add_argument("--watch-contracts", action="store_true")
    args = parser.parse_args()
    if args.watch_contracts:
        watch_contracts()
        return 0
    generate()
    commands = [
        [sys.executable, "-m", "uvicorn", "edgerunners_api.main:app", "--reload",
         "--host", os.getenv("EDGERUNNERS_HOST", "127.0.0.1"),
         "--port", os.getenv("EDGERUNNERS_PORT", "8000"),
         "--reload-dir", "apps/api/src", "--reload-dir", "packages"],
        [sys.executable, "scripts/dev.py", "--watch-contracts"],
    ]
    if args.android:
        commands.append(["./gradlew", "--continuous", ":app:assembleDebug"])
    processes = []
    try:
        for command in commands:
            cwd = ROOT / "apps/android" if command[0] == "./gradlew" else ROOT
            processes.append(subprocess.Popen(command, cwd=cwd, start_new_session=True))
        while all(p.poll() is None for p in processes):
            time.sleep(0.25)
        return next(p.returncode for p in processes if p.poll() is not None) or 1
    except KeyboardInterrupt:
        return 0
    finally:
        for process in processes:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
        for process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    raise SystemExit(main())
