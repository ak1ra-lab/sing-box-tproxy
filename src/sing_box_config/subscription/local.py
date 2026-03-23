from pathlib import Path
from typing import Any

from sing_box_config.subscription.base import SubscriptionSource


class LocalSubscriptionSource(SubscriptionSource):
    def fetch(self, config: dict[str, Any]) -> list[str]:
        raw: list[str] = list(config.get("paths", []))
        if "path" in config:
            raw.append(config["path"])
        # deduplicate while preserving order; Path is hashable
        paths = list(dict.fromkeys(Path(p) for p in raw))
        if not paths:
            raise ValueError("Local subscription missing 'path' or 'paths'")

        results = []
        for path in paths:
            if not path.exists():
                raise FileNotFoundError(f"Local subscription file not found: {path}")
            results.append(path.read_text(encoding="utf-8"))
        return results
