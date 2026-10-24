"""
Alias entrypoint for bridge.py.
Allows running `python onfloor_bridge_client.py` with identical arguments.
"""
import sys
import asyncio
import logging
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

import bridge

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        asyncio.run(bridge.main())
    except KeyboardInterrupt:
        pass
    except Exception as error:
        logging.getLogger("onfloor.bridge").error(
            "Bridge stopped (%s). Check configuration, audio devices and native dependencies.",
            type(error).__name__,
        )
        raise SystemExit(1)
