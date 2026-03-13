import logging
from typing import Any

import httpx
import tenacity

from sing_box_config.subscription.base import SubscriptionSource

logger = logging.getLogger(__name__)


@tenacity.retry(
    stop=tenacity.stop_after_attempt(5),
    wait=tenacity.wait_exponential_jitter(initial=1, max=30),
    before_sleep=tenacity.before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def fetch_url_with_retries(url: str, **kwargs: Any) -> httpx.Response:
    resp = httpx.get(url, **kwargs)
    resp.raise_for_status()
    return resp


class RemoteSubscriptionSource(SubscriptionSource):
    def fetch(self, config: dict[str, Any]) -> str:
        url = config.get("url")
        if not url:
            raise ValueError("Remote subscription missing 'url'")
        resp = fetch_url_with_retries(url, follow_redirects=True)
        logger.debug("resp.text = %s", resp.text[:100])
        return resp.text
