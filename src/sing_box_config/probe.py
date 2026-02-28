# PYTHON_ARGCOMPLETE_OK

import argparse
import asyncio
import contextlib
import signal
import subprocess
from typing import Any

import argcomplete
import httpx
from chaos_utils.logging import setup_logger

logger = setup_logger(__name__)


async def probe_http_get(
    client: httpx.AsyncClient,
    url: str,
    timeout: float,
    expected_status: list[int],
) -> bool:
    """
    Perform an HTTP GET liveness check against the given URL.

    The caller is responsible for managing the AsyncClient lifecycle so that
    the connection pool is reused across successive probe calls.

    Args:
        client: Shared httpx.AsyncClient instance
        url: The URL to probe
        timeout: Request timeout in seconds
        expected_status: List of HTTP status codes considered healthy

    Returns:
        True if the response status is in expected_status, False otherwise
    """
    try:
        resp = await client.get(url, timeout=timeout, follow_redirects=False)
        is_healthy = resp.status_code in expected_status
        if not is_healthy:
            logger.warning(
                "liveness probe unexpected status",
                extra={
                    "url": url,
                    "status_code": resp.status_code,
                    "expected_status": expected_status,
                },
            )
        return is_healthy
    except httpx.TimeoutException as exc:
        logger.warning(
            "liveness probe timed out",
            extra={"url": url, "error": str(exc)},
        )
        return False
    except Exception as exc:
        logger.warning(
            "liveness probe failed with exception",
            extra={"url": url, "error": str(exc)},
        )
        return False


def run_action(action: list[str]) -> None:
    """Execute the configured failure action as a subprocess."""
    logger.info(
        "liveness failure threshold reached, executing action",
        extra={"action": action},
    )
    try:
        result = subprocess.run(
            action,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            logger.error(
                "action exited with non-zero code",
                extra={
                    "action": action,
                    "returncode": result.returncode,
                    "stderr": result.stderr.strip(),
                },
            )
        else:
            logger.info(
                "action completed successfully",
                extra={"action": action},
            )
    except subprocess.TimeoutExpired:
        logger.error("action timed out", extra={"action": action})
    except Exception as exc:
        logger.error(
            "action execution failed",
            extra={"action": action, "error": str(exc)},
        )


async def liveness_loop(
    url: str,
    interval: float,
    timeout: float,
    expected_status: list[int],
    failure_threshold: int,
    success_threshold: int,
    action: list[str],
    stop_event: asyncio.Event,
) -> None:
    """
    Main liveness probe event loop.

    Continuously probes the configured URL at the specified interval.
    A single httpx.AsyncClient is created for the entire lifetime of the loop
    so the connection pool is reused across successive probe calls.
    When consecutive failures reach failure_threshold, the action command
    is executed and the failure counter resets.

    Args:
        url: URL to probe
        interval: Seconds between each probe attempt
        timeout: Per-request timeout in seconds
        expected_status: List of HTTP status codes considered healthy
        failure_threshold: Consecutive failures before triggering action
        success_threshold: Consecutive successes to log a recovery event
        action: Command (as list of args) to run on failure threshold
        stop_event: asyncio.Event that signals a graceful shutdown
    """
    consecutive_failures = 0
    consecutive_successes = 0

    logger.info(
        "starting sing-box liveness probe",
        extra={
            "url": url,
            "interval_seconds": interval,
            "timeout_seconds": timeout,
            "expected_status": expected_status,
            "failure_threshold": failure_threshold,
            "success_threshold": success_threshold,
            "action": action,
        },
    )

    async with httpx.AsyncClient() as client:
        while not stop_event.is_set():
            healthy = await probe_http_get(client, url, timeout, expected_status)

            if healthy:
                if consecutive_failures > 0:
                    logger.info(
                        "liveness probe recovered",
                        extra={"url": url, "previous_failures": consecutive_failures},
                    )
                consecutive_failures = 0
                consecutive_successes += 1
                if consecutive_successes == success_threshold:
                    logger.debug(
                        "liveness probe healthy",
                        extra={
                            "url": url,
                            "consecutive_successes": consecutive_successes,
                        },
                    )
            else:
                consecutive_successes = 0
                consecutive_failures += 1
                logger.warning(
                    "liveness probe consecutive failure",
                    extra={
                        "url": url,
                        "consecutive_failures": consecutive_failures,
                        "failure_threshold": failure_threshold,
                    },
                )
                if consecutive_failures >= failure_threshold:
                    run_action(action)
                    consecutive_failures = 0

            try:
                await asyncio.wait_for(
                    asyncio.shield(stop_event.wait()),
                    timeout=interval,
                )
            except asyncio.TimeoutError:
                pass  # normal: interval elapsed, continue probing


async def run(args: Any) -> None:
    """Async entry point: sets up signal handlers and runs the probe loop."""
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(
            sig,
            lambda s=sig: (
                logger.info("received signal, shutting down", extra={"signal": s}),
                stop_event.set(),
            ),
        )

    probe_task = asyncio.create_task(
        liveness_loop(
            url=args.url,
            interval=args.interval,
            timeout=args.timeout,
            expected_status=args.expected_status,
            failure_threshold=args.failure_threshold,
            success_threshold=args.success_threshold,
            action=args.action,
            stop_event=stop_event,
        )
    )

    await stop_event.wait()
    probe_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await probe_task

    logger.info("sing-box liveness probe stopped")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Liveness probe for sing-box",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--url",
        default="https://www.google.com/generate_204",
        metavar="URL",
        help="URL to probe for liveness check",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=60.0,
        metavar="SECONDS",
        help="Interval between probe checks in seconds",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        metavar="SECONDS",
        help="Per-probe request timeout in seconds",
    )
    parser.add_argument(
        "--expected-status",
        type=int,
        nargs="+",
        default=[204],
        metavar="STATUS_CODE",
        help="One or more HTTP status codes indicating a healthy response (space-separated)",
    )
    parser.add_argument(
        "--failure-threshold",
        type=int,
        default=5,
        metavar="N",
        help="Consecutive failures before triggering the action",
    )
    parser.add_argument(
        "--success-threshold",
        type=int,
        default=1,
        metavar="N",
        help="Consecutive successes to log a recovery/healthy event",
    )
    parser.add_argument(
        "--action",
        nargs="+",
        default=["systemctl", "restart", "sing-box.service"],
        metavar="ARG",
        help="Command (and its arguments) to execute when failure threshold is reached",
    )

    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    asyncio.run(run(args))
