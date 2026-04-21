from sing_box_config.models import LocalSubscription
from sing_box_config.subscription.base import SubscriptionSource


class LocalSubscriptionSource(SubscriptionSource[LocalSubscription]):
    def fetch(self, config: LocalSubscription) -> list[str]:
        raw = list(config.paths)
        if config.path is not None:
            raw.append(config.path)
        # deduplicate while preserving order; Path is hashable
        paths = list(dict.fromkeys(raw))
        # paths is guaranteed non-empty by LocalSubscription validator

        results = []
        for path in paths:
            if not path.exists():
                raise FileNotFoundError(f"Local subscription file not found: {path}")
            results.append(path.read_text(encoding="utf-8"))
        return results
