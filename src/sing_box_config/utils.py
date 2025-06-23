import base64
import json
import logging
import random
import time

import httpx

logger = logging.getLogger(__name__)


def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False, indent=4, sort_keys=False))


def read_json(filename):
    with open(filename, "r", encoding="utf-8") as f:
        data = json.loads(f.read())
    return data


def b64decode(data: str):
    suffix = "=" * (4 - len(data) % 4)
    return base64.urlsafe_b64decode(data + suffix).decode("utf-8")


def fetch_url_with_retries(
    url: str,
    retries: int = 5,
    timeout: int = 60,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
) -> httpx.Response | None:
    """
    Fetch a URL with retry logic.

    Args:
        url: URL to fetch
        retries: Maximum number of retry attempts
        timeout: Timeout in seconds for each request
        base_delay: Base delay for exponential backoff in seconds
        max_delay: Maximum delay between retries in seconds

    Returns:
        httpx.Response if successful, None otherwise
    """
    for attempt in range(1, retries + 1):
        try:
            resp = httpx.get(url, follow_redirects=True, timeout=timeout)
            resp.raise_for_status()
            return resp

        except (httpx.RequestError, httpx.HTTPStatusError) as err:
            logger.warning("Attempt %d failed: %s", attempt, err)

            if attempt == retries:
                logger.error("Failed to fetch %s after %d attempts", url, retries)
                return None

            delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
            jitter = random.uniform(0.5, 1.5)
            delay = min(delay * jitter, max_delay)

            logger.info("Waiting %.2f seconds before retry...", delay)
            time.sleep(delay)

    return None
