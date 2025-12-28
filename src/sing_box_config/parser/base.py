from abc import ABC, abstractmethod
from typing import Any, Optional


class BaseParser(ABC):
    """
    Base class for protocol parsers.
    """

    @abstractmethod
    def parse(self, uri: str, tag_prefix: str = "") -> Optional[dict[str, Any]]:
        """
        Parse a single proxy configuration string (e.g. URI) into a sing-box outbound config.

        Args:
            uri: The configuration string/URI.
            tag_prefix: Prefix to add to the proxy tag.

        Returns:
            A dictionary representing the sing-box outbound configuration, or None if parsing fails.
        """
        pass
