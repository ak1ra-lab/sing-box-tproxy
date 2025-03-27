import base64
import json
import logging

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
