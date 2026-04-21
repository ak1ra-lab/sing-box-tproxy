import json

from sing_box_config.models import InlineSubscription
from sing_box_config.subscription.base import SubscriptionSource


class InlineSubscriptionSource(SubscriptionSource[InlineSubscription]):
    def fetch(self, config: InlineSubscription) -> list[str]:
        if config.outbounds:
            return [json.dumps(config.outbounds)]
        if config.content is not None:
            return [config.content]
        # InlineSubscription validator guarantees at least one is present
        raise ValueError("Inline subscription missing 'outbounds' or 'content'")
