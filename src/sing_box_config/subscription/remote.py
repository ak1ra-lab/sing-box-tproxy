import logging
from typing import Any

import httpx
import tenacity

from sing_box_config.models import RemoteSubscription
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


class RemoteSubscriptionSource(SubscriptionSource[RemoteSubscription]):
    def fetch(self, config: RemoteSubscription) -> list[str]:
        raw = list(config.urls)
        if config.url is not None:
            raw.append(config.url)
        # deduplicate while preserving order
        urls = list(dict.fromkeys(raw))
        # urls is guaranteed non-empty by RemoteSubscription validator

        results = []
        for url in urls:
            resp = fetch_url_with_retries(url, follow_redirects=True)
            logger.debug("resp.text = %s", resp.text[:100])
            results.append(resp.text)
        return results
