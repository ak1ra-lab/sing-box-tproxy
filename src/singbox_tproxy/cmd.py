#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
# author: ak1ra
# date: 2025-03-27

import argparse
import logging
import logging.config
from pathlib import Path

import argcomplete

from singbox_tproxy.config import log_dir, logging_config
from singbox_tproxy.export import save_config_from_subscriptions
from singbox_tproxy.utils import read_json

logger = logging.getLogger(__name__)


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
        help="sing-box base config",
    )
    parser.add_argument(
        "-s",
        "--subscriptions",
        type=Path,
        default="config/subscriptions.json",
        metavar="subscriptions.json",
        help="sing-box subscriptions config with subscriptions and outbounds",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default="files/etc/sing-box/config.json",
        metavar="config.json",
        help="sing-box output config",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )

    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    log_dir.mkdir(parents=True, exist_ok=True)

    logging.config.dictConfig(logging_config)
    if args.verbose:
        logging.root.setLevel(logging.DEBUG)
    else:
        logging.root.setLevel(logging.INFO)

    save_config_from_subscriptions(
        base_config=read_json(args.base),
        subscriptions_config=read_json(args.subscriptions),
        output=args.output,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    main()
