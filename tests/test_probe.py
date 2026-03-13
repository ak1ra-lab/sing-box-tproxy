import asyncio
import subprocess
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from sing_box_config.probe import (
    _maybe_run_action,
    liveness_loop,
    probe_http_get,
    run_action,
)

# Helpers
URL = "https://www.google.com/generate_204"
ACTION = ["systemctl", "restart", "sing-box.service"]


def _mock_response(status_code: int) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    return resp


# probe_http_get
def test_probe_http_get_healthy_single_status():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = _mock_response(204)

    result = asyncio.run(
        probe_http_get(mock_client, URL, timeout=5.0, expected_status=[204])
    )

    assert result is True
    mock_client.get.assert_awaited_once_with(URL, timeout=5.0, follow_redirects=False)


def test_probe_http_get_healthy_multiple_status():
    """Both 200 and 204 are acceptable; response returns 200."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = _mock_response(200)

    result = asyncio.run(
        probe_http_get(mock_client, URL, timeout=5.0, expected_status=[200, 204])
    )

    assert result is True


def test_probe_http_get_unhealthy_status():
    """Response status not in expected list → False."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = _mock_response(403)

    result = asyncio.run(
        probe_http_get(mock_client, URL, timeout=5.0, expected_status=[204])
    )

    assert result is False


def test_probe_http_get_timeout():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.side_effect = httpx.TimeoutException("timed out")

    result = asyncio.run(
        probe_http_get(mock_client, URL, timeout=5.0, expected_status=[204])
    )

    assert result is False


def test_probe_http_get_generic_exception():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.side_effect = RuntimeError("unexpected")

    result = asyncio.run(
        probe_http_get(mock_client, URL, timeout=5.0, expected_status=[204])
    )

    assert result is False


# run_action
def test_run_action_success():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stderr="")
        run_action(ACTION)

    mock_run.assert_called_once_with(ACTION, capture_output=True, text=True, timeout=30)


def test_run_action_nonzero_returncode():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stderr="failed")
        run_action(ACTION)  # must not raise

    mock_run.assert_called_once()


def test_run_action_timeout():
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(ACTION, 30)):
        run_action(ACTION)  # must not raise


def test_run_action_exception():
    with patch("subprocess.run", side_effect=OSError("no such file")):
        run_action(ACTION)  # must not raise


# _maybe_run_action
def test_maybe_run_action_executes_when_under_threshold():
    """action_count < action_threshold → run_action is called and count incremented."""
    with patch("sing_box_config.probe.run_action") as mock_run:
        new_count = _maybe_run_action(
            action=ACTION, action_count=0, action_threshold=3, url=URL
        )
    mock_run.assert_called_once_with(ACTION)
    assert new_count == 1


def test_maybe_run_action_suppresses_at_threshold():
    """action_count == action_threshold → run_action is NOT called, count unchanged."""
    with patch("sing_box_config.probe.run_action") as mock_run:
        new_count = _maybe_run_action(
            action=ACTION, action_count=3, action_threshold=3, url=URL
        )
    mock_run.assert_not_called()
    assert new_count == 3


def test_maybe_run_action_suppresses_above_threshold():
    """action_count > action_threshold → run_action is NOT called, count unchanged."""
    with patch("sing_box_config.probe.run_action") as mock_run:
        new_count = _maybe_run_action(
            action=ACTION, action_count=5, action_threshold=3, url=URL
        )
    mock_run.assert_not_called()
    assert new_count == 5


# liveness_loop
def _make_probe_side_effect(
    results: list[bool], stop_event: asyncio.Event, trigger_after: int
):
    """
    Returns an async side_effect function. Sets stop_event after trigger_after calls
    so the loop exits cleanly without blocking the test.
    """
    counter = {"n": 0}

    async def _probe(*_args, **_kwargs) -> bool:
        counter["n"] += 1
        value = results[min(counter["n"] - 1, len(results) - 1)]
        if counter["n"] >= trigger_after:
            stop_event.set()
        return value

    return _probe


def test_liveness_loop_triggers_action_at_threshold():
    """
    failure_threshold=3: after 3 consecutive failures run_action must be called once
    and the counter must reset.
    """
    stop_event = asyncio.Event()
    # 3 failures → action → stop
    side_effect = _make_probe_side_effect(
        [False, False, False], stop_event, trigger_after=3
    )

    with patch("sing_box_config.probe.probe_http_get", side_effect=side_effect):
        with patch("sing_box_config.probe.run_action") as mock_action:
            asyncio.run(
                liveness_loop(
                    url=URL,
                    interval=0,
                    timeout=5.0,
                    expected_status=[204],
                    failure_threshold=3,
                    success_threshold=1,
                    action=ACTION,
                    action_threshold=3,
                    stop_event=stop_event,
                )
            )

    mock_action.assert_called_once_with(ACTION)


def test_liveness_loop_no_action_below_threshold():
    """Only 2 failures with threshold=3 → action must NOT be called."""
    stop_event = asyncio.Event()
    side_effect = _make_probe_side_effect([False, False], stop_event, trigger_after=2)

    with patch("sing_box_config.probe.probe_http_get", side_effect=side_effect):
        with patch("sing_box_config.probe.run_action") as mock_action:
            asyncio.run(
                liveness_loop(
                    url=URL,
                    interval=0,
                    timeout=5.0,
                    expected_status=[204],
                    failure_threshold=3,
                    success_threshold=1,
                    action=ACTION,
                    action_threshold=3,
                    stop_event=stop_event,
                )
            )

    mock_action.assert_not_called()


def test_liveness_loop_counter_resets_after_action():
    """
    threshold=2; send 2 failures (action fires), then 1 more failure, then stop.
    Action must be called exactly once (counter reset after first trigger).
    """
    stop_event = asyncio.Event()
    # 2 failures → action → 1 more failure → stop (total 3 calls)
    side_effect = _make_probe_side_effect(
        [False, False, False], stop_event, trigger_after=3
    )

    with patch("sing_box_config.probe.probe_http_get", side_effect=side_effect):
        with patch("sing_box_config.probe.run_action") as mock_action:
            asyncio.run(
                liveness_loop(
                    url=URL,
                    interval=0,
                    timeout=5.0,
                    expected_status=[204],
                    failure_threshold=2,
                    success_threshold=1,
                    action=ACTION,
                    action_threshold=3,
                    stop_event=stop_event,
                )
            )

    # threshold=2, 3 failures total: fires at call 2, counter resets to 0,
    # call 3 brings counter to 1 (below threshold) → action called once.
    mock_action.assert_called_once_with(ACTION)


def test_liveness_loop_recovery_resets_failure_counter():
    """
    2 failures followed by a success: action must NOT fire because the success
    resets the failure counter before the threshold is reached.
    """
    stop_event = asyncio.Event()
    # False, False, True → stop after 3 calls; threshold=3 means action fires
    # only on 3 *consecutive* failures.  After the success counter resets.
    side_effect = _make_probe_side_effect(
        [False, False, True], stop_event, trigger_after=3
    )

    with patch("sing_box_config.probe.probe_http_get", side_effect=side_effect):
        with patch("sing_box_config.probe.run_action") as mock_action:
            asyncio.run(
                liveness_loop(
                    url=URL,
                    interval=0,
                    timeout=5.0,
                    expected_status=[204],
                    failure_threshold=3,
                    success_threshold=1,
                    action=ACTION,
                    action_threshold=3,
                    stop_event=stop_event,
                )
            )

    mock_action.assert_not_called()


def test_liveness_loop_action_suppressed_after_action_threshold():
    """
    failure_threshold=2, action_threshold=1:
    First 2 failures → action fires (action_count → 1).
    Next 2 failures → action is suppressed (action_count already == threshold).
    Total: run_action called exactly once.
    """
    stop_event = asyncio.Event()
    # 4 failures: trigger at call 4
    side_effect = _make_probe_side_effect(
        [False, False, False, False], stop_event, trigger_after=4
    )

    with patch("sing_box_config.probe.probe_http_get", side_effect=side_effect):
        with patch("sing_box_config.probe.run_action") as mock_action:
            asyncio.run(
                liveness_loop(
                    url=URL,
                    interval=0,
                    timeout=5.0,
                    expected_status=[204],
                    failure_threshold=2,
                    success_threshold=1,
                    action=ACTION,
                    action_threshold=1,
                    stop_event=stop_event,
                )
            )

    mock_action.assert_called_once_with(ACTION)


def test_liveness_loop_action_count_resets_on_recovery():
    """
    failure_threshold=2, action_threshold=1:
    2 failures → action fires.
    1 success → action_count resets to 0.
    2 more failures → action fires again.
    Total: run_action called exactly twice.
    """
    stop_event = asyncio.Event()
    # F F T F F  → stop after 5 calls
    side_effect = _make_probe_side_effect(
        [False, False, True, False, False], stop_event, trigger_after=5
    )

    with patch("sing_box_config.probe.probe_http_get", side_effect=side_effect):
        with patch("sing_box_config.probe.run_action") as mock_action:
            asyncio.run(
                liveness_loop(
                    url=URL,
                    interval=0,
                    timeout=5.0,
                    expected_status=[204],
                    failure_threshold=2,
                    success_threshold=1,
                    action=ACTION,
                    action_threshold=1,
                    stop_event=stop_event,
                )
            )

    assert mock_action.call_count == 2


def test_liveness_loop_stops_on_event():
    """Setting stop_event before the loop starts should exit immediately."""
    stop_event = asyncio.Event()
    stop_event.set()

    with patch("sing_box_config.probe.probe_http_get") as mock_probe:
        asyncio.run(
            liveness_loop(
                url=URL,
                interval=0,
                timeout=5.0,
                expected_status=[204],
                failure_threshold=3,
                success_threshold=1,
                action=ACTION,
                action_threshold=3,
                stop_event=stop_event,
            )
        )

    mock_probe.assert_not_called()
