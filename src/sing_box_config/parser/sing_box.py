import json
import logging
from typing import Any

from sing_box_config.parser.base import SubscriptionParser

logger = logging.getLogger(__name__)


class SingBoxSubscriptionParser(SubscriptionParser):
    def parse(self, content: str) -> list[dict[str, Any]]:
        try:
            data = json.loads(content)
        except json.JSONDecodeError as err:
            logger.warning("Failed to decode sing-box subscription: %s", err)
            return []

        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and "outbounds" in data:
            # Handle full config file
            return data["outbounds"]
        else:
            logger.warning("Invalid sing-box subscription format")
            return []
