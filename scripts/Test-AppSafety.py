"""Offline application regressions: fake input only, offscreen Qt, disposable INI.

Run with .runtime/python/python.exe -I scripts/Test-AppSafety.py.
Optional --report PATH writes machine-readable workload measurements.
"""
import argparse
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import random
import sys
import tempfile
import threading
import time
import tracemalloc
import unittest
from unittest.mock import patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"
root = Path(__file__).resolve().parents[1]
loader = importlib.machinery.SourceFileLoader("audited_clicker", str(root / "Auto Clicker.pyw"))
spec = importlib.util.spec_from_loader(loader.name, loader)
appmod = importlib.util.module_from_spec(spec)
sys.modules[loader.name] = appmod
import_started = time.perf_counter()
loader.exec_module(appmod)
measurements = {"module_import_seconds": time.perf_counter() - import_started}
application = appmod.QApplication.instance() or appmod.QApplication([])


def values(**changes):
    base = dict(rate_mode=appmod.RATE_CPS, rate_value="500", button="Left",
                click_type=appmod.CLICK_ONCE, repeat_mode=appmod.REPEAT_COUNT,
                repeat_value="10", start_delay="0", variation_percent="0",
                target_mode=appmod.TARGET_CURSOR, target_x="0", target_y="0")
    base.update(changes)
    return base


class Clock:
    value = 0.0

    def now(self):
        return self.value

    def wait(self, deadline, event):
        self.value = max(self.value, deadline)
        return event.is_set()


class ClickerSafety(unittest.TestCase):
    def test_oversized_count_rejected_as_validation_error(self):
        with self.assertRaises(ValueError):
            appmod.build_config(values(repeat_value="9" * 400))

    def test_numeric_and_enum_boundaries(self):
        for field, invalid in {
            "rate_value": ["nan", "inf", "-inf", "0", "500.001", "oops"],
            "repeat_value": ["0", "-1", "1.5", "1000000001"],
            "start_delay": ["-0.1", "3600.1", "nan"],
            "variation_percent": ["-1", "50.01", "inf"],
            "button": ["unknown"], "click_type": ["unknown"],
            "rate_mode": ["unknown"], "repeat_mode": ["unknown"],
            "target_mode": ["unknown"],
        }.items():
            for value in invalid:
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    appmod.build_config(values(**{field: value}))
        for field in ("target_x", "target_y"):
            with self.assertRaises(ValueError):
                appmod.build_config(values(target_mode=appmod.TARGET_FIXED, **{field: "1000001"}))

    def test_cancel_during_position_does_not_click(self):
        event = threading.Event()

        class Mouse(appmod.FakeMouse):
            def move_to(self, x, y):
                event.set()

        mouse = Mouse()
        state, count, _ = appmod.run_click_loop(
            appmod.build_config(values(target_mode=appmod.TARGET_FIXED)), event, mouse,
            lambda count: None, lambda text: None, random.Random(0))
        self.assertEqual((state, count, mouse.clicks), ("stopped", 0, []))

    def test_duration_expiring_during_position_does_not_click(self):
        clock = Clock()

        class Mouse(appmod.FakeMouse):
            def move_to(self, x, y):
                clock.value = 1.0

        mouse = Mouse()
        state, count, _ = appmod.run_click_loop(
            appmod.build_config(values(target_mode=appmod.TARGET_FIXED,
                repeat_mode=appmod.REPEAT_SECONDS, repeat_value="0.1")),
            threading.Event(), mouse, lambda count: None, lambda text: None,
            random.Random(0), clock.wait, clock.now)
        self.assertEqual((state, count, mouse.clicks), ("completed", 0, []))

    def test_hotkey_failure_directly_stops_active_worker(self):
        event = threading.Event()

        def failed_reader(_):
            raise OSError("injected failure")

        monitor = appmod.HotkeyMonitor(appmod.UiBridge(), appmod.DEFAULT_HOTKEY_VK,
                                       0, key_state_reader=failed_reader)
        monitor.set_active_stop_event(event)
        monitor.start()
        monitor.join(1)
        self.assertFalse(monitor.is_alive())
        self.assertTrue(event.is_set(), "Safety stop must not depend on Qt signal delivery")

    def test_unavailable_emergency_hotkey_blocks_new_job(self):
        with tempfile.TemporaryDirectory(prefix="clicker-audit-") as temporary:
            window = appmod.AutoClicker(testing=True, settings_path=Path(temporary) / "settings.ini")
            window.testing = False
            window.mouse = appmod.FakeMouse()
            window.hotkey_available = False
            try:
                window.start_clicking()
                self.assertFalse(window.running)
            finally:
                if window.worker_stop is not None:
                    window.worker_stop.set()
                if window.worker_thread is not None:
                    window.worker_thread.join(1)
                application.processEvents()
                window.testing = True
                window.close()
                window.deleteLater()
                application.sendPostedEvents(None, appmod.QEvent.DeferredDelete)

    def test_partial_send_releases_only_unpaired_button_down(self):
        packet = (appmod.Input * 4)()
        release = (appmod.Input * 1)()
        for inserted in range(4):
            calls = []

            def sender(count, packet, size):
                calls.append(count)
                return inserted if len(calls) == 1 else 1

            with self.assertRaises(OSError):
                appmod._build_click_sender(sender, packet, release, appmod.ctypes.sizeof(appmod.Input))()
            self.assertEqual(calls, [4, 1] if inserted % 2 else [4])

    def test_pre_cancelled_start_delay_is_bounded(self):
        event = threading.Event()
        event.set()
        started = time.perf_counter()
        result = appmod.run_click_job(appmod.build_config(values(start_delay="3600")), event, appmod.FakeMouse())
        self.assertEqual(result[:2], ("stopped", 0))
        self.assertLess(time.perf_counter() - started, 0.1)

    def test_fake_scheduler_workload_and_callback_throttling(self):
        clock = Clock()
        count_updates = []

        class Mouse:
            count = 0

            def prepare_click(self, button, double_click):
                def send():
                    self.count += 1
                return send

        mouse = Mouse()
        tracemalloc.start()
        started = time.perf_counter()
        result = appmod.run_click_loop(appmod.build_config(values(repeat_value="100000")),
            threading.Event(), mouse, count_updates.append, lambda text: None,
            random.Random(0), clock.wait, clock.now)
        elapsed = time.perf_counter() - started
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        measurements.update(fake_100000_actions_seconds=elapsed,
                            fake_100000_actions_peak_python_bytes=peak,
                            fake_100000_actions_count_callbacks=len(count_updates))
        self.assertEqual(result[:2], ("completed", 100000))
        self.assertEqual(mouse.count, 100000)
        self.assertLess(len(count_updates), 2100)
        self.assertLess(elapsed, 10.0)
        self.assertLess(peak, 2 * 1024 * 1024)

    def test_offscreen_startup_log_bounds_and_preferences(self):
        with tempfile.TemporaryDirectory(prefix="clicker-audit-") as temporary:
            settings = Path(temporary) / "settings.ini"
            started = time.perf_counter()
            window = appmod.AutoClicker(testing=True, settings_path=settings)
            measurements["offscreen_window_startup_seconds"] = time.perf_counter() - started
            self.assertLess(measurements["offscreen_window_startup_seconds"], 5.0)
            for index in range(750):
                window.append_log(str(index))
            self.assertLessEqual(window.log_box.document().blockCount(), 500)
            window.rate_input.setText("37")
            window.close()
            restored = appmod.AutoClicker(testing=True, settings_path=settings)
            self.assertEqual(restored.rate_input.text(), "37")
            restored.close()
            window.deleteLater()
            restored.deleteLater()
            application.sendPostedEvents(None, appmod.QEvent.DeferredDelete)

    def test_realtime_fake_worker_cpu_stop_and_qt_heartbeat(self):
        event = threading.Event()
        mouse = appmod.FakeMouse()
        results = []
        beats = []
        timer = appmod.QTimer()
        timer.setInterval(10)
        timer.timeout.connect(lambda: beats.append(time.perf_counter()))
        timer.start()
        config = appmod.build_config(values(rate_value="200", repeat_mode=appmod.REPEAT_MANUAL))
        started = time.perf_counter()
        cpu_started = time.process_time()
        worker = threading.Thread(target=lambda: results.append(appmod.run_click_loop(
            config, event, mouse, lambda count: None, lambda text: None, random.Random(0))))
        worker.start()
        try:
            while time.perf_counter() - started < 0.30:
                application.processEvents()
                time.sleep(0.002)
            stop_started = time.perf_counter()
            event.set()
            worker.join(1)
            stop_latency = time.perf_counter() - stop_started
        finally:
            event.set()
            worker.join(1)
            timer.stop()
        elapsed = time.perf_counter() - started
        cpu = time.process_time() - cpu_started
        gaps = [later - earlier for earlier, later in zip(beats, beats[1:])]
        measurements.update(realtime_fake_worker_seconds=elapsed,
            realtime_fake_worker_cpu_seconds=cpu, realtime_fake_worker_actions=len(mouse.clicks),
            realtime_fake_worker_stop_latency_seconds=stop_latency,
            realtime_fake_worker_qt_heartbeat_count=len(beats),
            realtime_fake_worker_qt_max_gap_seconds=max(gaps, default=0))
        self.assertFalse(worker.is_alive())
        self.assertEqual(results[0][0], "stopped")
        self.assertGreaterEqual(len(mouse.clicks), 35)
        self.assertLessEqual(len(mouse.clicks), 65)
        self.assertLess(stop_latency, 0.2)
        self.assertGreaterEqual(len(beats), 10)
        self.assertLess(max(gaps, default=0), 0.2)
        self.assertLess(cpu, elapsed * 0.85 + 0.05)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ClickerSafety))
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(dict(tests=result.testsRun, failures=len(result.failures),
            errors=len(result.errors), measurements=measurements), indent=2) + "\n", encoding="utf-8")
    raise SystemExit(not result.wasSuccessful())
