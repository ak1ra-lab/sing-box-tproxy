from abc import ABC, abstractmethod
from typing import Any


class SubscriptionSource(ABC):
    """Base class for subscription content fetchers."""

    @abstractmethod
    def fetch(self, config: dict[str, Any]) -> str:
        """
        Fetch subscription content and return it as a raw string.

        Args:
            config: Subscription configuration dict.

        Returns:
            Raw subscription content as a string.

        Raises:
            ValueError: If required config fields are missing or invalid.
            FileNotFoundError: If a local file path doesn't exist.
        """
        pass
