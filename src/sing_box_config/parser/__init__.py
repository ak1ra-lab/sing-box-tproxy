from typing import Optional

from sing_box_config.parser.base import SubscriptionParser
from sing_box_config.parser.shadowsocks import SIP002SubscriptionParser
from sing_box_config.parser.sing_box import SingBoxSubscriptionParser

SUPPORTED_FORMATS = {
    "sip002": SIP002SubscriptionParser,
    "sing-box": SingBoxSubscriptionParser,
}


def get_parser(format_type: str) -> Optional[SubscriptionParser]:
    parser_cls = SUPPORTED_FORMATS.get(format_type.lower())
    if parser_cls:
        return parser_cls()
    return None
