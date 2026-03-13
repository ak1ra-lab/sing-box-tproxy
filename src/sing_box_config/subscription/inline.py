import json
from typing import Any

from sing_box_config.subscription.base import SubscriptionSource


class InlineSubscriptionSource(SubscriptionSource):
    def fetch(self, config: dict[str, Any]) -> str:
        if "outbounds" in config:
            return json.dumps(config["outbounds"])
        if "content" in config:
            return config["content"]
        raise ValueError("Inline subscription missing 'outbounds' or 'content'")
