from sing_box_config.subscription.base import SubscriptionSource
from sing_box_config.subscription.inline import InlineSubscriptionSource
from sing_box_config.subscription.local import LocalSubscriptionSource
from sing_box_config.subscription.remote import RemoteSubscriptionSource

SOURCE_MAP: dict[str, type[SubscriptionSource]] = {
    "inline": InlineSubscriptionSource,
    "local": LocalSubscriptionSource,
    "remote": RemoteSubscriptionSource,
}


def get_source(sub_type: str) -> SubscriptionSource | None:
    cls = SOURCE_MAP.get(sub_type.lower())
    return cls() if cls else None
