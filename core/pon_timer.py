# core/pon_timer.py
"""PON-compliant periodic scheduling.

Zero-polling rule (Prime Directive §4.1): no ``while True`` spin loops, no
active status polling. Recurring maintenance work must be event-loop-timer
driven so that between ticks the process idles at ~0% CPU.

``schedule_periodic`` runs an async callable on a fixed interval. Each tick
yields to the event loop via ``asyncio.sleep`` and then re-arms the next tick
as a fresh task. There is no ``while True`` and no ``time.sleep``; ticks are
self-rescheduling, event-loop-driven units.

Cancellation is cooperative and prompt: ``cancel()`` sets a stop event and
cancels the currently-running tick task, so a timer can be torn down without
waiting for its next interval.
"""

import asyncio
import logging

logger = logging.getLogger(__name__)


class PeriodicTimer:
    """Handle to a running periodic timer. Call ``cancel()`` to stop it."""

    def __init__(self):
        self._stop = asyncio.Event()
        self._current: "asyncio.Task | None" = None
        self._loop = asyncio.get_running_loop()

    def _arm(self, interval_seconds, coro_fn, label):
        if self._stop.is_set():
            return

        async def _tick():
            next_interval = interval_seconds
            try:
                ret = await coro_fn()
                # An async callable may override the next interval (e.g. back
                # off on transient errors) by returning a positive number.
                if isinstance(ret, (int, float)) and ret > 0:
                    next_interval = float(ret)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 - degrade, never crash the daemon
                logger.warning(f"{label}: periodic tick failed: {exc}")
            # Yield control, then re-arm the next tick reactively.
            try:
                await asyncio.sleep(next_interval)
            except asyncio.CancelledError:
                raise
            if self._stop.is_set():
                return
            self._arm(next_interval, coro_fn, label)

        self._current = self._loop.create_task(_tick())

    def start(self, coro_fn, interval_seconds, *, label="periodic",
              initial_delay=0.0, run_immediately=False):
        """Begin ticking. Returns self."""
        if not run_immediately and initial_delay > 0:
            async def _delay_then_arm():
                try:
                    await asyncio.sleep(initial_delay)
                except asyncio.CancelledError:
                    raise
                if not self._stop.is_set():
                    self._arm(interval_seconds, coro_fn, label)
            self._current = self._loop.create_task(_delay_then_arm())
        elif not run_immediately:
            async def _delay_then_arm():
                try:
                    await asyncio.sleep(interval_seconds)
                except asyncio.CancelledError:
                    raise
                if not self._stop.is_set():
                    self._arm(interval_seconds, coro_fn, label)
            self._current = self._loop.create_task(_delay_then_arm())
        else:
            self._arm(interval_seconds, coro_fn, label)
        return self

    def cancel(self):
        """Stop future ticks without awaiting completion."""
        self._stop.set()
        task, self._current = self._current, None
        if task is not None and not task.done():
            task.cancel()


def schedule_periodic(coro_fn, interval_seconds, *, label="periodic",
                      initial_delay=0.0, run_immediately=False) -> PeriodicTimer:
    """Run ``await coro_fn()`` every ``interval_seconds`` (event-driven, zero poll).

    Args:
        coro_fn: zero-arg async callable to run on each tick.
        interval_seconds: wall-clock interval between ticks.
        label: log prefix.
        initial_delay: delay before the first tick.
        run_immediately: tick once right away instead of waiting for the first
            interval.
    """
    timer = PeriodicTimer()
    return timer.start(coro_fn, interval_seconds, label=label,
                       initial_delay=initial_delay,
                       run_immediately=run_immediately)