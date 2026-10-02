"""Offline tests of the CI fixture policy; never load Qt or call Windows APIs.

Extract only the policy/guard definitions from the actual workflow script. Its
top-level CI gate and native-input path are deliberately never executed here.
"""

import ast
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import threading
import time
import unittest


SOURCE = Path(__file__).with_name("Test-RepresentativeWorkflow.py")
TREE = ast.parse(SOURCE.read_text(encoding="utf-8"))


def definitions(namespace, names):
    selected = [
        node for node in TREE.body
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in names
    ]
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(SOURCE), "exec"), namespace)
    return namespace


class Clock:
    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def monotonic(self):
        return self.now

    def sleep(self, delay):
        self.sleeps.append(delay)
        self.now += delay


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = definitions({"ctypes": ctypes, "time": time}, {
            "placement_candidates", "wait_for_owned_target", "native_client_center",
        })

    def function(self, name):
        self.assertTrue(name in self.policy, f"Missing regression policy: {name}")
        return self.policy[name]

    def wait(self, probe, candidates=((0, 0),), place=None, pump=None, **kwargs):
        self.clock = Clock()
        self.placements = []
        self.pumps = []
        return self.function("wait_for_owned_target")(
            candidates, 42, place or self.placements.append, probe,
            pump or (lambda: self.pumps.append(self.clock.now)),
            clock=self.clock.monotonic, sleep=self.clock.sleep,
            timeout=kwargs.pop("timeout", 2.0),
            placement_timeout=kwargs.pop("placement_timeout", 0.5),
            stable_for=kwargs.pop("stable_for", 0.1),
            poll_interval=0.02, **kwargs,
        )

    def test_placement_covers_center_and_corners_within_available_screen(self):
        positions = self.function("placement_candidates")((100, 200, 1200, 800), (260, 180))
        self.assertEqual(positions[0], (570, 510))
        self.assertEqual(len(positions), 9)
        self.assertEqual(len(set(positions)), 9)
        self.assertTrue(all(100 <= x <= 1040 and 200 <= y <= 820 for x, y in positions))
        self.assertIn((124, 224), positions)
        self.assertIn((1016, 796), positions)

    def test_small_screen_deduplicates_candidates(self):
        self.assertEqual(self.function("placement_candidates")((-10, -20, 260, 180), (260, 180)),
                         ((-10, -20),))

    def test_target_larger_than_available_screen_fails_closed(self):
        with self.assertRaisesRegex(AssertionError, "fit"):
            self.function("placement_candidates")((0, 0, 200, 180), (260, 180))

    def test_owned_point_must_remain_stable_before_ready(self):
        self.assertEqual(self.wait(lambda: ((10, 20), 42)), (10, 20))
        self.assertGreaterEqual(self.clock.now, 0.1)
        self.assertGreaterEqual(len(self.pumps), 5)
        self.assertEqual(self.placements, [(0, 0)])

    def test_transient_overlay_is_waited_out_without_moving_other_windows(self):
        def probe():
            return (10, 20), 999 if self.clock.now < 0.14 else 42
        self.assertEqual(self.wait(probe), (10, 20))
        self.assertGreaterEqual(self.clock.now, 0.24)
        self.assertEqual(self.placements, [(0, 0)])

    def test_permanent_center_overlay_uses_an_alternate_own_placement(self):
        def probe():
            return (10, 20), 999 if self.placements[-1] == (0, 0) else 42
        self.assertEqual(self.wait(probe, candidates=((0, 0), (100, 200))), (10, 20))
        self.assertEqual(self.placements, [(0, 0), (100, 200)])

    def test_event_processing_is_required_for_native_readiness(self):
        state = {"ready": False}
        def pump():
            state["ready"] = True
        self.assertEqual(self.wait(lambda: ((10, 20), 42 if state["ready"] else 999), pump=pump), (10, 20))

    def test_changing_native_point_restarts_stability(self):
        def probe():
            return ((10, 20) if self.clock.now < 0.06 else (30, 40)), 42
        self.assertEqual(self.wait(probe), (30, 40))
        self.assertGreaterEqual(self.clock.now, 0.16)

    def test_one_foreign_hit_restarts_stability(self):
        def probe():
            return (10, 20), 999 if 0.06 <= self.clock.now < 0.08 else 42
        self.assertEqual(self.wait(probe), (10, 20))
        self.assertGreaterEqual(self.clock.now, 0.18)

    def test_permanently_foreign_or_null_hit_is_bounded_and_fail_closed(self):
        for owner in (0, 999):
            with self.subTest(owner=owner):
                with self.assertRaisesRegex(AssertionError, "refusing to send clicks"):
                    self.wait(lambda: ((10, 20), owner), timeout=1.3)
                self.assertLessEqual(self.clock.now, 1.3)
                self.assertLessEqual(len(self.placements), 3)

    def test_readiness_at_deadline_is_not_accepted(self):
        self.function("wait_for_owned_target")
        def probe():
            return (10, 20), 42 if self.clock.now >= 0.96 else 999
        with self.assertRaises(AssertionError):
            self.wait(probe, timeout=1.0)
        self.assertLessEqual(self.clock.now, 1.0)

    def test_native_probe_error_is_not_suppressed_or_retried(self):
        def probe():
            raise RuntimeError("probe failed")
        with self.assertRaisesRegex(RuntimeError, "probe failed"):
            self.wait(probe)
        self.assertEqual(self.clock.now, 0)

    def test_slow_event_pump_cannot_accept_ownership_after_deadline(self):
        def pump():
            self.clock.now += 2
        with self.assertRaisesRegex(AssertionError, "refusing to send clicks"):
            self.wait(lambda: ((10, 20), 42), timeout=1.0, pump=pump)
        self.assertEqual(self.clock.sleeps, [])

    def test_invalid_bounds_are_rejected_before_placement(self):
        wait = self.function("wait_for_owned_target")
        for change in ({"timeout": float("inf")}, {"timeout": float("nan")},
                       {"timeout": 0}, {"poll_interval": 0}, {"stable_for": 1}):
            with self.subTest(change=change):
                placed = []
                with self.assertRaises(ValueError):
                    wait(((0, 0),), 42, placed.append, lambda: ((10, 20), 42), lambda: None,
                         **change)
                self.assertEqual(placed, [])

    def test_place_target_touches_only_its_own_native_handle(self):
        moved, native_calls = [], []
        fixture = SimpleNamespace(move=lambda *args: moved.append(args),
                                  raise_=lambda: None, activateWindow=lambda: None)
        namespace = definitions({
            "target": fixture, "application": SimpleNamespace(processEvents=lambda: None),
            "ctypes": SimpleNamespace(set_last_error=lambda _value: None, get_last_error=lambda: 0),
            "user32": SimpleNamespace(SetWindowPos=lambda *args: native_calls.append(args) or True),
            "module": SimpleNamespace(wintypes=wintypes, HWND_TOPMOST=-1, TOPMOST_POSITION_FLAGS=0x213),
            "handle": 42, "SWP_SHOWWINDOW": 0x40,
        }, {"place_target"})
        self.assertTrue("place_target" in namespace)
        namespace["place_target"]((100, 200))
        self.assertEqual(moved, [(100, 200)])
        self.assertEqual(len(native_calls), 1)
        self.assertEqual(native_calls[0][0].value, 42)
        self.assertEqual(native_calls[0][-1], 0x253)

    def test_native_center_uses_client_to_screen_not_qt_logical_coordinates(self):
        class Native:
            def GetClientRect(self, _handle, rect):
                rect._obj.left, rect._obj.top = 0, 0
                rect._obj.right, rect._obj.bottom = 390, 270  # 150% Qt scale
                return True
            def ClientToScreen(self, _handle, point):
                point._obj.x += 600
                point._obj.y += 300
                return True
        self.assertEqual(self.function("native_client_center")(Native(), 42, wintypes), (795, 435))

    def test_failed_or_empty_native_client_rect_is_rejected(self):
        native_center = self.function("native_client_center")
        for rect_ok, mapping_ok, size in ((False, True, 10), (True, False, 10), (True, True, 0)):
            with self.subTest(rect_ok=rect_ok, mapping_ok=mapping_ok, size=size):
                class Native:
                    def GetClientRect(self, _handle, rect):
                        rect._obj.right = rect._obj.bottom = size
                        return rect_ok
                    def ClientToScreen(self, _handle, _point):
                        return mapping_ok
                with self.assertRaises(AssertionError):
                    native_center(Native(), 42, wintypes)


class ClickGuardTests(unittest.TestCase):
    def setUp(self):
        self.hit = 42
        self.cursor = (10, 20)
        self.inside = True
        self.sent = []
        test = self
        class Native:
            def GetClientRect(self, _handle, rect):
                rect._obj.right = rect._obj.bottom = 100
                return True
            def ScreenToClient(self, _handle, point):
                if not test.inside:
                    point._obj.x = 1000
                return True
            def WindowFromPoint(self, _point):
                return test.hit
        class Mouse:
            def cursor_position(self):
                return test.cursor
            def prepare_click(self, _button, _double_click=False):
                return lambda: test.sent.append("click")
        self.namespace = definitions({
            "module": SimpleNamespace(wintypes=wintypes, WindowsMouseController=Mouse),
            "ctypes": ctypes, "user32": Native(), "handle": 42,
            "click_point": (10, 20), "click_lock": threading.Lock(),
            "hit_diagnostics": lambda _hit: " same_root_is_not_ownership",
        }, {"assert_target_at_cursor", "GuardedMouseController"})
        self.mouse = self.namespace["GuardedMouseController"]()

    def test_exact_owned_point_can_send(self):
        self.mouse.prepare_click("Left")()
        self.assertEqual(self.sent, ["click"])

    def test_every_actual_click_rechecks_exact_ownership(self):
        send = self.mouse.prepare_click("Left")
        send()
        self.hit = 999
        with self.assertRaisesRegex(AssertionError, "refusing to send clicks"):
            send()
        self.assertEqual(self.sent, ["click"])

    def test_foreign_or_null_or_same_root_child_never_sends(self):
        for hit in (0, 999, 43):
            with self.subTest(hit=hit):
                self.hit = hit
                with self.assertRaises(AssertionError):
                    self.mouse.prepare_click("Left")()
        self.assertEqual(self.sent, [])

    def test_cursor_displacement_never_sends(self):
        self.cursor = (11, 20)
        with self.assertRaisesRegex(AssertionError, "Cursor moved"):
            self.mouse.prepare_click("Left")()
        self.assertEqual(self.sent, [])

    def test_outside_client_area_never_sends(self):
        self.inside = False
        with self.assertRaisesRegex(AssertionError, "outside"):
            self.mouse.prepare_click("Left")()
        self.assertEqual(self.sent, [])


class EntryGateTests(unittest.TestCase):
    def test_non_ci_non_arm_and_offscreen_environments_stop_before_native_imports(self):
        for github, arch, platform, message in (
            ("false", "ARM64", "windows", "restricted"),
            ("true", "AMD64", "windows", "restricted"),
            ("true", "ARM64", "offscreen", "native Windows"),
        ):
            with self.subTest(github=github, arch=arch, platform=platform):
                environment = dict(os.environ, GITHUB_ACTIONS=github, RUNNER_ARCH=arch,
                                   QT_QPA_PLATFORM=platform)
                result = subprocess.run([sys.executable, "-I", str(SOURCE)], env=environment,
                                        capture_output=True, text=True, timeout=5)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stderr)
                self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
