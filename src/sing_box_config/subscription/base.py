from abc import ABC, abstractmethod
from typing import Any


class SubscriptionSource(ABC):
    """Base class for subscription content fetchers."""

    @abstractmethod
    def fetch(self, config: dict[str, Any]) -> list[str]:
        """
        Fetch subscription content and return it as a list of raw strings.

        Each element corresponds to one source (path, URL, or inline content).
        Callers should iterate over the list and parse each item independently.

        Args:
            config: Subscription configuration dict.

        Returns:
            List of raw subscription content strings.

        Raises:
            ValueError: If required config fields are missing or invalid.
            FileNotFoundError: If a local file path doesn't exist.
        """
        pass
