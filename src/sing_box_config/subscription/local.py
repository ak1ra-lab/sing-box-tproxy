from pathlib import Path
from typing import Any

from sing_box_config.subscription.base import SubscriptionSource


class LocalSubscriptionSource(SubscriptionSource):
    def fetch(self, config: dict[str, Any]) -> str:
        path = Path(config["path"])
        if not path.exists():
            raise FileNotFoundError(f"Local subscription file not found: {path}")
        return path.read_text(encoding="utf-8")
