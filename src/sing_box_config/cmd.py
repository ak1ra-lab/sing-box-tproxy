#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK

import argparse
from pathlib import Path

import argcomplete

from sing_box_config.export import save_config_from_subscriptions
from sing_box_config.logging import setup_logger

logger = setup_logger(__name__)


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
        "-r",
        "--retries",
        type=int,
        default=5,
        help="Maximum number of retry attempts, default: %(default)s",
    )
    parser.add_argument(
        "-t",
        "--timeout",
        type=int,
        default=60,
        help="Timeout in seconds for each request, default: %(default)s",
    )

    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    save_config_from_subscriptions(args)


if __name__ == "__main__":
    main()
