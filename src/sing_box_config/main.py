# PYTHON_ARGCOMPLETE_OK

import argparse
from pathlib import Path

import argcomplete
from chaos_utils.logging import setup_json_logger
from chaos_utils.text_utils import read_json

from sing_box_config.export import save_config_from_subscriptions

logger = setup_json_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="The configuration generator for sing-box"
    )
    parser.add_argument(
        "-b",
        "--base",
        type=Path,
        default="config/base.json",
        metavar="base.json",
        help="sing-box base config, default: %(default)s",
    )
    parser.add_argument(
        "-s",
        "--subscriptions",
        type=Path,
        default="config/subscriptions.json",
        metavar="subscriptions.json",
        help="sing-box subscriptions config with subscriptions and outbounds, default: %(default)s",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default="config/config.json",
        metavar="config.json",
        help="sing-box output config, default: %(default)s",
    )
    parser.add_argument(
        "--proxies-path",
        type=Path,
        default="config/proxies.json",
        metavar="proxies.json",
        help="Path to store/load fetched proxies, default: %(default)s",
    )
    parser.add_argument(
        "--use-cache",
        action="store_true",
        help="Use cached proxies from proxies-path if available",
    )

    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    base_config = read_json(Path(args.base))
    subscriptions_config = read_json(Path(args.subscriptions))
    output_path = Path(args.output)
    proxies_path = Path(args.proxies_path)
    save_config_from_subscriptions(
        base_config=base_config,
        subscriptions_config=subscriptions_config,
        output_path=output_path,
        proxies_path=proxies_path,
        use_cache=args.use_cache,
    )
