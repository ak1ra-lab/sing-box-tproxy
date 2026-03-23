import json
import logging
from typing import Any

from sing_box_config.parser.base import SubscriptionParser

logger = logging.getLogger(__name__)

# sing-box outbound types that are selector/proxy groups, not real proxy nodes
_GROUP_TYPES: frozenset[str] = frozenset({"selector", "urltest"})


class SingBoxSubscriptionParser(SubscriptionParser):
    def parse(self, content: str) -> list[dict[str, Any]]:
        try:
            data = json.loads(content)
        except json.JSONDecodeError as err:
            logger.warning("Failed to decode sing-box subscription: %s", err)
            return []

        if isinstance(data, list):
            outbounds = data
        elif isinstance(data, dict) and "outbounds" in data:
            # Handle full config file
            outbounds = data["outbounds"]
        else:
            logger.warning("Invalid sing-box subscription format")
            return []

        return [p for p in outbounds if p.get("type") not in _GROUP_TYPES]
