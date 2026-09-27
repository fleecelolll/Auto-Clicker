"""Send bounded real clicks only to a disposable test window on CI ARM64.

This intentionally refuses to run on a person's desktop. It exercises the
actual Windows SendInput path and verifies the target receives the clicks.
"""

import importlib.machinery
import importlib.util
import os
from pathlib import Path
import sys
import threading
import time


if os.environ.get("GITHUB_ACTIONS") != "true" or os.environ.get("RUNNER_ARCH") != "ARM64":
    raise SystemExit("Real click workflow is restricted to disposable GitHub Windows ARM64 runners.")
if os.environ.get("QT_QPA_PLATFORM", "windows").lower() != "windows":
    raise SystemExit("The real click workflow requires a native Windows Qt window.")

release = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(release))

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QApplication, QWidget


loader = importlib.machinery.SourceFileLoader(
    "fleece_click_representative", str(release / "Auto Clicker.pyw")
)
spec = importlib.util.spec_from_loader(loader.name, loader)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
loader.exec_module(module)


class ClickTarget(QWidget):
    def __init__(self):
        super().__init__()
        self.received = 0
        self.setWindowTitle("Fleece disposable click target")
        self.setAttribute(Qt.WA_NativeWindow)
        self.resize(260, 180)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.received += 1
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.received += 1
        super().mouseDoubleClickEvent(event)


application = QApplication.instance() or QApplication([])
screen = application.primaryScreen()
if screen is None:
    raise AssertionError("No interactive screen is available for real click testing.")
rect = screen.availableGeometry()
target = ClickTarget()
target.move(rect.x() + max(0, (rect.width() - target.width()) // 2), rect.y() + max(0, (rect.height() - target.height()) // 2))
target.show()
target.raise_()
target.activateWindow()
application.processEvents()

user32 = module.NATIVE_USER32
user32.SetForegroundWindow.argtypes = (module.wintypes.HWND,)
user32.SetForegroundWindow.restype = module.wintypes.BOOL
user32.GetForegroundWindow.argtypes = ()
user32.GetForegroundWindow.restype = module.wintypes.HWND
handle = int(target.winId())
user32.SetForegroundWindow(handle)
if int(user32.GetForegroundWindow()) != handle:
    target.close()
    raise AssertionError("The disposable target could not be made foreground; refusing to send clicks.")

point = target.mapToGlobal(QPoint(target.width() // 2, target.height() // 2))
mouse = module.WindowsMouseController()
if not mouse.virtual_screen_contains(point.x(), point.y()):
    target.close()
    raise AssertionError("The disposable target is outside the virtual screen.")
prior_position = mouse.cursor_position()
values = {
    "rate_mode": module.RATE_CPS,
    "rate_value": "1",
    "button": "Left",
    "click_type": module.CLICK_ONCE,
    "repeat_mode": module.REPEAT_COUNT,
    "repeat_value": "3",
    "start_delay": "0",
    "variation_percent": "0",
    "target_mode": module.TARGET_FIXED,
    "target_x": str(point.x()),
    "target_y": str(point.y()),
}
config = module.build_config(values)
outcome = {}


def run():
    try:
        outcome["result"] = module.run_click_job(config, threading.Event(), mouse)
    except BaseException as error:
        outcome["error"] = error


worker = threading.Thread(target=run, name="FleeceRepresentativeClick", daemon=True)
try:
    worker.start()
    deadline = time.monotonic() + 12
    while worker.is_alive() and time.monotonic() < deadline:
        application.processEvents()
        time.sleep(0.01)
    worker.join(timeout=0.1)
    application.processEvents()
    if worker.is_alive():
        raise AssertionError("The bounded click worker did not finish.")
    if "error" in outcome:
        raise outcome["error"]
    state, actions, _message = outcome.get("result", (None, None, None))
    if state != "completed" or actions != 3 or target.received != 3:
        raise AssertionError(
            f"Expected three real clicks on the disposable target; got state={state}, actions={actions}, received={target.received}."
        )
    print("Real Windows SendInput -> disposable Qt target: 3 of 3 clicks received.")
finally:
    mouse.move_to(*prior_position)
    target.close()
    application.processEvents()
