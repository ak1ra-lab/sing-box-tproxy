from abc import ABC, abstractmethod
from typing import Any, Optional


class URIParser(ABC):
    """
    Base class for single URI parsers (e.g. ss://, vmess://).
    """

    @abstractmethod
    def parse(self, uri: str) -> Optional[dict[str, Any]]:
        """
        Parse a single proxy configuration string (e.g. URI) into a sing-box outbound config.

        Args:
            uri: The configuration string/URI.

        Returns:
            A dictionary representing the sing-box outbound configuration, or None if parsing fails.
        """
        pass


class SubscriptionParser(ABC):
    """
    Base class for subscription content parsers.
    """

    @abstractmethod
    def parse(self, content: str) -> list[dict[str, Any]]:
        """
        Parse subscription content into a list of sing-box outbound configs.

        Args:
            content: The raw subscription content (usually text).

        Returns:
            A list of dictionary representing the sing-box outbound configurations.
        """
        pass
