# PYTHON_ARGCOMPLETE_OK

import argparse
from pathlib import Path

import argcomplete
from chaos_utils.logging import setup_logger
from chaos_utils.text_utils import read_json
from pydantic import ValidationError

from sing_box_config.export import save_config_from_subscriptions
from sing_box_config.models import BaseConfig, subscription_adapter

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

    try:
        logger.info(
            "starting sing-box config generation",
            extra={
                "base": str(args.base),
                "subscriptions": str(args.subscriptions),
                "output": str(args.output),
                "proxies_path": str(args.proxies_path),
                "use_cache": args.use_cache,
            },
        )

        raw_base = read_json(args.base)
        try:
            base_config = BaseConfig.model_validate(raw_base)
        except ValidationError as e:
            logger.error("Invalid base config %s: %s", args.base, e)
            raise SystemExit(1) from e

        raw_subscriptions = read_json(args.subscriptions)
        if not isinstance(raw_subscriptions, dict):
            logger.error(
                "Invalid subscriptions config %s: expected a JSON object",
                args.subscriptions,
            )
            raise SystemExit(1)
        subscriptions_config = {}
        for name, entry in raw_subscriptions.items():
            try:
                subscriptions_config[name] = subscription_adapter.validate_python(entry)
            except ValidationError as e:
                logger.warning("Invalid subscription %r, skipping: %s", name, e)

        output_path = args.output
        proxies_path = args.proxies_path

        save_config_from_subscriptions(
            base_config=base_config,
            subscriptions_config=subscriptions_config,
            output_path=output_path,
            proxies_path=proxies_path,
            use_cache=args.use_cache,
        )
        logger.info(
            "sing-box config generation completed", extra={"output": str(output_path)}
        )

    except Exception as e:
        logger.error(
            "sing-box config generation failed",
            extra={"error": str(e)},
            exc_info=True,
        )
        raise
