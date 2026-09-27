"""Send bounded real clicks only to a disposable test window on CI ARM64.

This intentionally refuses to run on a person's desktop. It exercises the
actual Windows SendInput path and verifies the target receives the clicks.
"""

import importlib.machinery
import importlib.util
import ctypes
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
        self.setWindowFlag(Qt.WindowStaysOnTopHint)
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
user32.WindowFromPoint.argtypes = (module.wintypes.POINT,)
user32.WindowFromPoint.restype = module.wintypes.HWND
user32.GetClientRect.argtypes = (
    module.wintypes.HWND,
    ctypes.POINTER(module.wintypes.RECT),
)
user32.GetClientRect.restype = module.wintypes.BOOL
user32.ScreenToClient.argtypes = (
    module.wintypes.HWND,
    ctypes.POINTER(module.wintypes.POINT),
)
user32.ScreenToClient.restype = module.wintypes.BOOL
user32.GetAncestor.argtypes = (module.wintypes.HWND, module.wintypes.UINT)
user32.GetAncestor.restype = module.wintypes.HWND
user32.GetWindowThreadProcessId.argtypes = (
    module.wintypes.HWND,
    ctypes.POINTER(module.wintypes.DWORD),
)
user32.GetWindowThreadProcessId.restype = module.wintypes.DWORD
user32.GetClassNameW.argtypes = (
    module.wintypes.HWND,
    module.wintypes.LPWSTR,
    ctypes.c_int,
)
user32.GetClassNameW.restype = ctypes.c_int
user32.GetThreadDesktop.argtypes = (module.wintypes.DWORD,)
user32.GetThreadDesktop.restype = module.wintypes.HANDLE
user32.GetUserObjectInformationW.argtypes = (
    module.wintypes.HANDLE,
    ctypes.c_int,
    ctypes.c_void_p,
    module.wintypes.DWORD,
    ctypes.POINTER(module.wintypes.DWORD),
)
user32.GetUserObjectInformationW.restype = module.wintypes.BOOL
kernel32 = module.NATIVE_KERNEL32
kernel32.GetCurrentThreadId.argtypes = ()
kernel32.GetCurrentThreadId.restype = module.wintypes.DWORD
kernel32.ProcessIdToSessionId.argtypes = (
    module.wintypes.DWORD,
    ctypes.POINTER(module.wintypes.DWORD),
)
kernel32.ProcessIdToSessionId.restype = module.wintypes.BOOL
kernel32.WTSGetActiveConsoleSessionId.argtypes = ()
kernel32.WTSGetActiveConsoleSessionId.restype = module.wintypes.DWORD
handle = int(target.winId())
# Native topmost placement can raise our fixture above a runner shell overlay
# without requiring foreground activation. The hit-test below remains mandatory.
SWP_SHOWWINDOW = 0x0040
ctypes.set_last_error(0)
if not user32.SetWindowPos(
    module.wintypes.HWND(handle),
    module.HWND_TOPMOST,
    0,
    0,
    0,
    0,
    module.TOPMOST_POSITION_FLAGS | SWP_SHOWWINDOW,
):
    target.close()
    error_code = ctypes.get_last_error()
    if error_code:
        raise ctypes.WinError(error_code)
    raise AssertionError("Could not show the disposable target as a topmost window.")
application.processEvents()
point = target.mapToGlobal(QPoint(target.width() // 2, target.height() // 2))
click_point = (point.x(), point.y())
click_lock = threading.Lock()


def hit_diagnostics(hit):
    """Report only window structure and session state, never window titles."""
    try:
        owner = module.wintypes.DWORD()
        user32.GetWindowThreadProcessId(hit, ctypes.byref(owner))
        root = int(user32.GetAncestor(hit, 2) or 0)  # GA_ROOT
        window_class = ctypes.create_unicode_buffer(128)
        user32.GetClassNameW(hit, window_class, len(window_class))
        desktop = user32.GetThreadDesktop(kernel32.GetCurrentThreadId())
        receives_input = module.wintypes.BOOL()
        needed = module.wintypes.DWORD()
        has_input_state = bool(
            desktop
            and user32.GetUserObjectInformationW(
                desktop, 6, ctypes.byref(receives_input), ctypes.sizeof(receives_input), ctypes.byref(needed)
            )
        )  # UOI_IO
        session = module.wintypes.DWORD()
        has_session = bool(kernel32.ProcessIdToSessionId(os.getpid(), ctypes.byref(session)))
        console_session = kernel32.WTSGetActiveConsoleSessionId()
        return (
            f" hit_root={root:#x}, hit_same_process={owner.value == os.getpid()},"
            f" hit_class={window_class.value!r}, desktop_receives_input="
            f"{bool(receives_input.value) if has_input_state else 'unknown'},"
            f" process_session={session.value if has_session else 'unknown'},"
            f" console_session={console_session}"
        )
    except Exception as error:
        return f" diagnostics_unavailable={type(error).__name__}"


def assert_target_at_cursor(mouse):
    """A real SendInput click is safe only while it hit-tests to our widget."""
    cursor = mouse.cursor_position()
    if cursor != click_point:
        raise AssertionError(f"Cursor moved away from the disposable target: {cursor}.")
    client = module.wintypes.RECT()
    local = module.wintypes.POINT(*cursor)
    if not user32.GetClientRect(handle, ctypes.byref(client)) or not user32.ScreenToClient(
        handle, ctypes.byref(local)
    ):
        raise AssertionError("Could not verify the disposable target's client rectangle.")
    if not (client.left <= local.x < client.right and client.top <= local.y < client.bottom):
        raise AssertionError("The click point is outside the disposable target's client area.")
    hit = int(user32.WindowFromPoint(module.wintypes.POINT(*cursor)) or 0)
    if hit != handle:
        raise AssertionError(
            f"The disposable target does not own the click point (target={handle:#x}, hit={hit:#x});"
            f" refusing to send clicks.{hit_diagnostics(hit)}"
        )


class GuardedMouseController(module.WindowsMouseController):
    def prepare_click(self, button, double_click=False):
        send_click = super().prepare_click(button, double_click)

        def send_only_to_target():
            with click_lock:
                assert_target_at_cursor(self)
                send_click()

        return send_only_to_target


mouse = GuardedMouseController()
if not mouse.virtual_screen_contains(*click_point):
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
    "target_x": str(click_point[0]),
    "target_y": str(click_point[1]),
}
config = module.build_config(values)
outcome = {}
stop_event = threading.Event()


def run():
    try:
        outcome["result"] = module.run_click_job(config, stop_event, mouse)
    except BaseException as error:
        outcome["error"] = error


worker = threading.Thread(target=run, name="FleeceRepresentativeClick", daemon=True)
try:
    mouse.move_to(*click_point)
    application.processEvents()
    assert_target_at_cursor(mouse)
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
    stop_event.set()
    if worker.ident is not None:
        worker.join(timeout=2)
    with click_lock:
        try:
            mouse.move_to(*prior_position)
        finally:
            target.close()
    application.processEvents()
