import atexit
import ctypes
import os
import random
import subprocess
import sys
import threading
import time
import traceback
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path


APP_NAME = "Auto Clicker"
APP_VERSION = "1.0.2"
APP_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = APP_DIR / ".runtime"
SETTINGS_PATH = RUNTIME_DIR / "settings.ini"
SETUP_LOCK_DIR = RUNTIME_DIR / "setup.lock"
VENV_PYTHON = APP_DIR / ".venv" / "Scripts" / "python.exe"
VENV_PYTHONW = APP_DIR / ".venv" / "Scripts" / "pythonw.exe"
EMBEDDED_PYTHON = RUNTIME_DIR / "python" / "python.exe"
EMBEDDED_PYTHONW = RUNTIME_DIR / "python" / "pythonw.exe"
APP_MUTEX_NAMES = (
    r"Global\FleeceAutoClickerApp",
    r"Local\FleeceAutoClickerApp",
)
APP_MUTEX_NAME = APP_MUTEX_NAMES[0]
APP_MUTEX_HANDLE = None


def show_native_error(message, title=APP_NAME):
    if os.name == "nt":
        ctypes.windll.user32.MessageBoxW(None, message, title, 0x10)
    else:
        print(f"{title}: {message}", file=sys.stderr)


def native_question(message, title=APP_NAME, owner=None):
    if os.name != "nt":
        return True
    owner_handle = wintypes.HWND(int(owner)) if owner else None
    return ctypes.windll.user32.MessageBoxW(owner_handle, message, title, 0x24) == 6


def bootstrap_local_python():
    current = os.path.normcase(os.path.realpath(sys.executable))
    for local_python, local_pythonw in (
        (VENV_PYTHON, VENV_PYTHONW),
        (EMBEDDED_PYTHON, EMBEDDED_PYTHONW),
    ):
        valid_executables = {
            os.path.normcase(os.path.realpath(path))
            for path in (local_python, local_pythonw)
            if path.is_file()
        }
        if current in valid_executables and sys.flags.isolated:
            return
        if not local_python.is_file() or not local_pythonw.is_file():
            continue
        try:
            validation = subprocess.run(
                [str(local_python), "-I", "-c", "pass"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=8,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if validation.returncode != 0:
                continue
            subprocess.Popen(
                [
                    str(local_pythonw),
                    "-I",
                    str(Path(__file__).resolve()),
                    *sys.argv[1:],
                ],
                cwd=str(APP_DIR),
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except (OSError, subprocess.SubprocessError):
            continue
        raise SystemExit(0)

    show_native_error(
        "Setup is missing, incomplete, or no longer usable.\n\n"
        "Run Installer.bat, let it finish, then open the Auto Clicker shortcut."
    )
    raise SystemExit(1)


if __name__ == "__main__":
    bootstrap_local_python()


try:
    from PySide6.QtCore import (
        QEasingCurve,
        QEvent,
        QPoint,
        QPropertyAnimation,
        QRect,
        QSettings,
        QTimer,
        Qt,
        Signal,
        QObject,
    )
    from PySide6.QtGui import (
        QCloseEvent,
        QKeyEvent,
        QMouseEvent,
        QPainter,
        QPen,
        QTextCursor,
    )
    from PySide6.QtWidgets import (
        QApplication,
        QCheckBox,
        QFrame,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMainWindow,
        QPushButton,
        QScrollArea,
        QSizePolicy,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )
except Exception:
    if __name__ == "__main__":
        show_native_error(
            "Setup is incomplete and the app window cannot load.\n\n"
            "Run Installer.bat again to repair the setup."
        )
        raise SystemExit(1)
    raise


def handle_unhandled_exception(error_type, error, trace):
    try:
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        (RUNTIME_DIR / "error.log").write_text(
            "".join(traceback.format_exception(error_type, error, trace)),
            encoding="utf-8",
        )
    except OSError:
        pass
    show_native_error(
        "The app stopped because of an unexpected error.\n\n"
        "Run Installer.bat again. If it still happens, check .runtime\\error.log."
    )
    application = QApplication.instance()
    if application is not None:
        application.quit()


MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
INPUT_MOUSE = 0
SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79
HWND_TOPMOST = wintypes.HWND(-1)
HWND_NOTOPMOST = wintypes.HWND(-2)
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010
SWP_NOOWNERZORDER = 0x0200
TOPMOST_POSITION_FLAGS = (
    SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE | SWP_NOOWNERZORDER
)
SCHEDULER_COARSE_GUARD_SECONDS = 0.020
SCHEDULER_SPIN_GUARD_SECONDS = 0.0005
SCHEDULER_RATE_GUARD_SECONDS = 0.00001
SCHEDULER_TIMER_MAX_WAIT_MS = 100
CREATE_WAITABLE_TIMER_HIGH_RESOLUTION = 0x00000002
TIMER_MODIFY_STATE = 0x0002
SYNCHRONIZE = 0x00100000
WAIT_OBJECT_0 = 0x00000000
ERROR_ACCESS_DENIED = 5
ERROR_ALREADY_EXISTS = 183

if os.name == "nt":
    NATIVE_USER32 = ctypes.WinDLL("user32", use_last_error=True)
    NATIVE_USER32.SetWindowPos.argtypes = (
        wintypes.HWND,
        wintypes.HWND,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.UINT,
    )
    NATIVE_USER32.SetWindowPos.restype = wintypes.BOOL
    NATIVE_USER32.IsWindow.argtypes = (wintypes.HWND,)
    NATIVE_USER32.IsWindow.restype = wintypes.BOOL
    NATIVE_WINMM = ctypes.WinDLL("winmm", use_last_error=True)
    NATIVE_WINMM.timeBeginPeriod.argtypes = (wintypes.UINT,)
    NATIVE_WINMM.timeBeginPeriod.restype = wintypes.UINT
    NATIVE_WINMM.timeEndPeriod.argtypes = (wintypes.UINT,)
    NATIVE_WINMM.timeEndPeriod.restype = wintypes.UINT
    NATIVE_KERNEL32 = ctypes.WinDLL("kernel32", use_last_error=True)
    NATIVE_KERNEL32.CreateWaitableTimerExW.argtypes = (
        ctypes.c_void_p,
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
    )
    NATIVE_KERNEL32.CreateWaitableTimerExW.restype = wintypes.HANDLE
    NATIVE_KERNEL32.SetWaitableTimer.argtypes = (
        wintypes.HANDLE,
        ctypes.POINTER(ctypes.c_longlong),
        wintypes.LONG,
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.BOOL,
    )
    NATIVE_KERNEL32.SetWaitableTimer.restype = wintypes.BOOL
    NATIVE_KERNEL32.WaitForSingleObject.argtypes = (
        wintypes.HANDLE,
        wintypes.DWORD,
    )
    NATIVE_KERNEL32.WaitForSingleObject.restype = wintypes.DWORD
    NATIVE_KERNEL32.CreateMutexW.argtypes = (
        ctypes.c_void_p,
        wintypes.BOOL,
        wintypes.LPCWSTR,
    )
    NATIVE_KERNEL32.CreateMutexW.restype = wintypes.HANDLE
    NATIVE_KERNEL32.CloseHandle.argtypes = (wintypes.HANDLE,)
    NATIVE_KERNEL32.CloseHandle.restype = wintypes.BOOL
else:
    NATIVE_USER32 = None
    NATIVE_WINMM = None
    NATIVE_KERNEL32 = None


class WindowsClickTiming:
    def __init__(self):
        self.period_enabled = False
        self.waitable_timer = None

    def __enter__(self):
        if NATIVE_WINMM is None:
            return self
        self.period_enabled = NATIVE_WINMM.timeBeginPeriod(1) == 0
        self.waitable_timer = NATIVE_KERNEL32.CreateWaitableTimerExW(
            None,
            None,
            CREATE_WAITABLE_TIMER_HIGH_RESOLUTION,
            TIMER_MODIFY_STATE | SYNCHRONIZE,
        )
        if not self.waitable_timer:
            self.waitable_timer = NATIVE_KERNEL32.CreateWaitableTimerExW(
                None,
                None,
                0,
                TIMER_MODIFY_STATE | SYNCHRONIZE,
            )
        return self

    def wait_until_deadline(self, deadline, stop_event):
        while True:
            if stop_event.is_set():
                return True
            remaining = deadline - time.perf_counter()
            if remaining <= 0:
                return False
            if remaining > SCHEDULER_COARSE_GUARD_SECONDS:
                if stop_event.wait(remaining - SCHEDULER_COARSE_GUARD_SECONDS):
                    return True
                continue
            if remaining <= SCHEDULER_SPIN_GUARD_SECONDS:
                continue
            if not self.waitable_timer:
                time.sleep(remaining - SCHEDULER_SPIN_GUARD_SECONDS)
                continue

            timer_wait = remaining - SCHEDULER_SPIN_GUARD_SECONDS
            due_time = ctypes.c_longlong(-max(1, int(timer_wait * 10_000_000)))
            if not NATIVE_KERNEL32.SetWaitableTimer(
                self.waitable_timer,
                ctypes.byref(due_time),
                0,
                None,
                None,
                False,
            ):
                time.sleep(remaining)
                continue
            timeout_ms = min(
                SCHEDULER_TIMER_MAX_WAIT_MS,
                max(1, int(timer_wait * 1000.0) + 2),
            )
            if (
                NATIVE_KERNEL32.WaitForSingleObject(
                    self.waitable_timer,
                    timeout_ms,
                )
                != WAIT_OBJECT_0
            ):
                time.sleep(max(0.0, deadline - time.perf_counter()))
            continue

    def __exit__(self, error_type, error, traceback_object):
        if self.waitable_timer:
            NATIVE_KERNEL32.CloseHandle(self.waitable_timer)
            self.waitable_timer = None
        if self.period_enabled:
            NATIVE_WINMM.timeEndPeriod(1)
        return False


def release_app_mutex():
    global APP_MUTEX_HANDLE
    if APP_MUTEX_HANDLE is None or NATIVE_KERNEL32 is None:
        return
    NATIVE_KERNEL32.CloseHandle(APP_MUTEX_HANDLE)
    APP_MUTEX_HANDLE = None


def _try_create_named_mutex(name):
    if NATIVE_KERNEL32 is None:
        return "unavailable", None
    ctypes.set_last_error(0)
    handle = NATIVE_KERNEL32.CreateMutexW(None, False, name)
    error_code = ctypes.get_last_error()
    if handle and error_code == ERROR_ALREADY_EXISTS:
        NATIVE_KERNEL32.CloseHandle(handle)
        return "exists", None
    if handle:
        return "acquired", handle
    if error_code == ERROR_ACCESS_DENIED:
        return "denied", None
    return "failed", None


def acquire_app_mutex():
    global APP_MUTEX_HANDLE, APP_MUTEX_NAME
    if NATIVE_KERNEL32 is None:
        return True
    for index, name in enumerate(APP_MUTEX_NAMES):
        status, handle = _try_create_named_mutex(name)
        if status == "acquired":
            APP_MUTEX_NAME = name
            APP_MUTEX_HANDLE = handle
            atexit.register(release_app_mutex)
            return True
        if status == "exists":
            return False
        if index == 0 and status == "denied":
            continue
        return False
    return False


class MouseInput(ctypes.Structure):
    _fields_ = (
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    )


class InputUnion(ctypes.Union):
    _fields_ = (("mi", MouseInput),)


class Input(ctypes.Structure):
    _anonymous_ = ("data",)
    _fields_ = (("type", wintypes.DWORD), ("data", InputUnion))


BUTTON_FLAGS = {
    "Left": (MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP),
    "Right": (MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP),
    "Middle": (MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP),
}


def _build_click_sender(sender, packet, release_packet, structure_size):
    packet_count = len(packet)

    def send_click():
        ctypes.set_last_error(0)
        inserted = sender(packet_count, packet, structure_size)
        if inserted == packet_count:
            return
        error_code = ctypes.get_last_error()
        if inserted % 2:
            sender(1, release_packet, structure_size)
        if error_code:
            raise ctypes.WinError(error_code)
        if inserted == 0:
            raise OSError(
                "Windows blocked the mouse input. An app running as administrator "
                "may require Auto Clicker to run with the same permission."
            )
        raise OSError(
            f"Windows inserted {inserted} of {packet_count} mouse inputs."
        )

    return send_click

LEGACY_HOTKEYS = {
    "F6": 0x75,
    "F7": 0x76,
    "F9": 0x78,
    "F10": 0x79,
    "F11": 0x7A,
    "F12": 0x7B,
}
EMERGENCY_HOTKEY = "F8"
EMERGENCY_VK = 0x77
DEFAULT_HOTKEY_VK = LEGACY_HOTKEYS["F6"]
HOTKEY_CTRL = 0x01
HOTKEY_ALT = 0x02
HOTKEY_SHIFT = 0x04
HOTKEY_WIN = 0x08
HOTKEY_MODIFIER_MASK = HOTKEY_CTRL | HOTKEY_ALT | HOTKEY_SHIFT | HOTKEY_WIN
MOUSE_VIRTUAL_KEYS = {0x01, 0x02, 0x04, 0x05, 0x06}
PURE_MODIFIER_VIRTUAL_KEYS = {
    0x10,
    0x11,
    0x12,
    0x5B,
    0x5C,
    0xA0,
    0xA1,
    0xA2,
    0xA3,
    0xA4,
    0xA5,
}
RATE_CPS = "Clicks per second"
RATE_DELAY = "Delay between clicks (milliseconds)"
CLICK_ONCE = "One click"
CLICK_DOUBLE = "Double click"
MAX_SINGLE_CPS = 500.0
MAX_DOUBLE_CPS = 250.0
REPEAT_MANUAL = "Only when I stop it"
REPEAT_COUNT = "After this many clicks"
REPEAT_SECONDS = "After this many seconds"
TARGET_CURSOR = "Follow the mouse cursor"
TARGET_FIXED = "Always click one saved spot"


def normalize_hotkey(virtual_key, modifiers):
    try:
        virtual_key = int(virtual_key)
    except (TypeError, ValueError, OverflowError):
        virtual_key = DEFAULT_HOTKEY_VK
    try:
        modifiers = int(modifiers) & HOTKEY_MODIFIER_MASK
    except (TypeError, ValueError, OverflowError):
        modifiers = 0
    if (
        not 1 <= virtual_key <= 0xFE
        or virtual_key == EMERGENCY_VK
        or virtual_key in MOUSE_VIRTUAL_KEYS
        or virtual_key in PURE_MODIFIER_VIRTUAL_KEYS
    ):
        return DEFAULT_HOTKEY_VK, 0
    return virtual_key, modifiers


@dataclass(frozen=True)
class ClickConfig:
    rate_mode: str
    rate_value: float
    button: str
    click_type: str
    repeat_mode: str
    repeat_value: float
    start_delay: float
    variation_percent: float
    target_mode: str
    target_x: int
    target_y: int

    @property
    def interval_seconds(self):
        if self.rate_mode == RATE_CPS:
            return 1.0 / self.rate_value
        return self.rate_value / 1000.0

    @property
    def double_click(self):
        return self.click_type == CLICK_DOUBLE


def parse_number(text, label):
    try:
        value = float(str(text).strip())
    except (TypeError, ValueError):
        raise ValueError(f"{label} must be a number.") from None
    if value != value or value in (float("inf"), float("-inf")):
        raise ValueError(f"{label} must be a normal number.")
    return value


def parse_integer(text, label):
    raw = str(text).strip()
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise ValueError(f"{label} must be a whole number.") from None
    return value


def maximum_cps(click_type):
    return MAX_DOUBLE_CPS if click_type == CLICK_DOUBLE else MAX_SINGLE_CPS


def minimum_delay_ms(click_type):
    return 1000.0 / maximum_cps(click_type)


def scheduled_interval_seconds(config, rng):
    interval = config.interval_seconds
    variation = config.variation_percent / 100.0
    if variation:
        interval *= rng.uniform(1.0 - variation, 1.0 + variation)
    hard_minimum = minimum_delay_ms(config.click_type) / 1000.0
    return max(hard_minimum, interval)


def build_config(values):
    button = values["button"]
    if button not in BUTTON_FLAGS:
        raise ValueError("Choose a valid mouse button.")
    click_type = values["click_type"]
    if click_type not in (CLICK_ONCE, CLICK_DOUBLE):
        raise ValueError("Choose one click or a double click.")

    rate_mode = values["rate_mode"]
    rate_value = parse_number(values["rate_value"], "Click rate")
    if rate_mode == RATE_CPS:
        rate_limit = maximum_cps(click_type)
        if not 0.1 <= rate_value <= rate_limit:
            if click_type == CLICK_DOUBLE:
                raise ValueError(
                    "Double-click mode supports 0.1 to 250 double-clicks per "
                    "second (500 individual clicks)."
                )
            raise ValueError(
                "One-click mode supports 0.1 to 500 clicks per second."
            )
    elif rate_mode == RATE_DELAY:
        minimum_delay = minimum_delay_ms(click_type)
        if not minimum_delay <= rate_value <= 3_600_000:
            minimum_text = f"{minimum_delay:g}"
            raise ValueError(
                f"The delay for {click_type.lower()} mode must be between "
                f"{minimum_text} and 3,600,000 milliseconds."
            )
    else:
        raise ValueError("Choose a valid timing mode.")

    repeat_mode = values["repeat_mode"]
    if repeat_mode == REPEAT_MANUAL:
        repeat_value = 0.0
    elif repeat_mode == REPEAT_COUNT:
        repeat_value = float(
            parse_integer(values["repeat_value"], "Number of clicks")
        )
        if not 1 <= repeat_value <= 1_000_000_000:
            raise ValueError(
                "The number of clicks must be between 1 and 1,000,000,000."
            )
    elif repeat_mode == REPEAT_SECONDS:
        repeat_value = parse_number(values["repeat_value"], "Number of seconds")
        if not 0.1 <= repeat_value <= 604_800:
            raise ValueError(
                "The number of seconds must be between 0.1 seconds and 7 days."
            )
    else:
        raise ValueError("Choose a valid repeat mode.")

    start_delay = parse_number(values["start_delay"], "Start delay")
    if not 0 <= start_delay <= 3600:
        raise ValueError("Start delay must be between 0 and 3600 seconds.")
    variation = parse_number(values["variation_percent"], "Random timing amount")
    if not 0 <= variation <= 50:
        raise ValueError("The random timing amount must be between 0 and 50 percent.")

    target_mode = values["target_mode"]
    target_x = 0
    target_y = 0
    if target_mode == TARGET_FIXED:
        target_x = parse_integer(values["target_x"], "X position")
        target_y = parse_integer(values["target_y"], "Y position")
        if not -1_000_000 <= target_x <= 1_000_000:
            raise ValueError("X position is outside the supported range.")
        if not -1_000_000 <= target_y <= 1_000_000:
            raise ValueError("Y position is outside the supported range.")
    elif target_mode != TARGET_CURSOR:
        raise ValueError("Choose where the app should click.")

    return ClickConfig(
        rate_mode=rate_mode,
        rate_value=rate_value,
        button=button,
        click_type=click_type,
        repeat_mode=repeat_mode,
        repeat_value=repeat_value,
        start_delay=start_delay,
        variation_percent=variation,
        target_mode=target_mode,
        target_x=target_x,
        target_y=target_y,
    )


class WindowsMouseController:
    def __init__(self):
        if os.name != "nt":
            raise OSError("Auto Clicker requires Windows.")
        self.user32 = NATIVE_USER32
        self.user32.SendInput.argtypes = (
            wintypes.UINT,
            ctypes.POINTER(Input),
            ctypes.c_int,
        )
        self.user32.SendInput.restype = wintypes.UINT
        self.user32.GetCursorPos.argtypes = (ctypes.POINTER(wintypes.POINT),)
        self.user32.GetCursorPos.restype = wintypes.BOOL
        self.user32.SetCursorPos.argtypes = (ctypes.c_int, ctypes.c_int)
        self.user32.SetCursorPos.restype = wintypes.BOOL
        self._click_senders = {}
        input_size = ctypes.sizeof(Input)
        send_input = self.user32.SendInput
        for button, (down, up) in BUTTON_FLAGS.items():
            for double_click in (False, True):
                flags = (down, up, down, up) if double_click else (down, up)
                inputs = (Input * len(flags))()
                for index, flag in enumerate(flags):
                    inputs[index].type = INPUT_MOUSE
                    inputs[index].mi = MouseInput(0, 0, 0, flag, 0, 0)
                key = (button, double_click)
                release_input = (Input * 1)()
                release_input[0].type = INPUT_MOUSE
                release_input[0].mi = MouseInput(0, 0, 0, up, 0, 0)
                self._click_senders[key] = _build_click_sender(
                    send_input,
                    inputs,
                    release_input,
                    input_size,
                )

    def cursor_position(self):
        point = wintypes.POINT()
        if not self.user32.GetCursorPos(ctypes.byref(point)):
            raise ctypes.WinError()
        return point.x, point.y

    def move_to(self, x, y):
        if not self.user32.SetCursorPos(int(x), int(y)):
            raise ctypes.WinError()

    def virtual_screen_contains(self, x, y):
        left = self.user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
        top = self.user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
        width = self.user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
        height = self.user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
        return left <= x < left + width and top <= y < top + height

    def click(self, button, double_click=False):
        self._click_senders[(button, bool(double_click))]()

    def prepare_click(self, button, double_click=False):
        return self._click_senders[(button, bool(double_click))]


def wait_until_deadline(deadline, stop_event):
    while True:
        if stop_event.is_set():
            return True
        remaining = deadline - time.perf_counter()
        if remaining <= 0:
            return False
        if remaining > SCHEDULER_COARSE_GUARD_SECONDS:
            coarse_wait = remaining - SCHEDULER_COARSE_GUARD_SECONDS
            if stop_event.wait(coarse_wait):
                return True
            continue
        if remaining > SCHEDULER_SPIN_GUARD_SECONDS:
            time.sleep(remaining - SCHEDULER_SPIN_GUARD_SECONDS)


def run_click_job(config, stop_event, mouse, on_count=None, on_status=None, rng=None):
    on_count = on_count or (lambda count: None)
    on_status = on_status or (lambda text: None)
    rng = rng or random.Random()

    if config.start_delay:
        deadline = time.perf_counter() + config.start_delay
        while True:
            remaining = deadline - time.perf_counter()
            if remaining <= 0:
                break
            on_status(f"Armed • starts in {remaining:.1f}s • F8 stops")
            if stop_event.wait(min(0.1, remaining)):
                return "stopped", 0, "Stopped before clicking started."

    with WindowsClickTiming() as timing:
        return run_click_loop(
            config,
            stop_event,
            mouse,
            on_count,
            on_status,
            rng,
            timing.wait_until_deadline,
        )


def run_click_loop(
    config,
    stop_event,
    mouse,
    on_count,
    on_status,
    rng,
    deadline_waiter=wait_until_deadline,
    clock=None,
):
    actions = 0
    perf_counter = clock or time.perf_counter
    stop_is_set = stop_event.is_set
    started = perf_counter()
    count_limit = (
        int(config.repeat_value) if config.repeat_mode == REPEAT_COUNT else None
    )
    duration_deadline = None
    if config.repeat_mode == REPEAT_SECONDS:
        duration_deadline = started + config.repeat_value

    fixed_target = config.target_mode == TARGET_FIXED
    move_to = mouse.move_to if fixed_target else None
    prepare_click = getattr(mouse, "prepare_click", None)
    if prepare_click is not None:
        send_click = prepare_click(config.button, config.double_click)
    else:
        click = mouse.click
        button = config.button
        double_click = config.double_click

        def send_click():
            click(button, double_click)

    interval = config.interval_seconds
    variation = config.variation_percent / 100.0
    if variation:
        interval_lower = 1.0 - variation
        interval_upper = 1.0 + variation
        minimum_interval = minimum_delay_ms(config.click_type) / 1000.0
        random_interval = rng.uniform

        def next_interval():
            return max(
                minimum_interval,
                interval * random_interval(interval_lower, interval_upper),
            )

    else:
        def next_interval():
            return interval

    on_status("Clicking • F8 stops immediately")
    last_count_update = 0.0

    while not stop_is_set():
        if count_limit is not None and actions >= count_limit:
            return "completed", actions, "Requested click count completed."
        if duration_deadline is not None and perf_counter() >= duration_deadline:
            return "completed", actions, "Requested duration completed."

        try:
            if move_to is not None:
                move_to(config.target_x, config.target_y)
            action_started = perf_counter()
            send_click()
        except OSError as error:
            return "failed", actions, f"Windows could not send the click: {error}"

        actions += 1
        now = perf_counter()
        if actions == 1 or now - last_count_update >= 0.1:
            on_count(actions)
            last_count_update = now

        if count_limit is not None and actions >= count_limit:
            on_count(actions)
            return "completed", actions, "Requested click count completed."

        base_interval = next_interval()
        next_due = action_started + base_interval + SCHEDULER_RATE_GUARD_SECONDS
        wait_deadline = (
            min(next_due, duration_deadline)
            if duration_deadline is not None
            else next_due
        )
        if deadline_waiter(wait_deadline, stop_event):
            break

    on_count(actions)
    return "stopped", actions, "Stopped safely."


class UiBridge(QObject):
    toggle_requested = Signal()
    stop_requested = Signal()
    count_changed = Signal("qlonglong")
    status_changed = Signal(str)
    job_finished = Signal(str, "qlonglong", str)


def hotkey_state_matches(virtual_key, modifiers, key_down):
    if not virtual_key or not key_down(virtual_key):
        return False
    ctrl_down = bool(key_down(0x11))
    alt_down = bool(key_down(0x12))
    shift_down = bool(key_down(0x10))
    win_down = bool(key_down(0x5B) or key_down(0x5C))
    return (
        ctrl_down == bool(modifiers & HOTKEY_CTRL)
        and alt_down == bool(modifiers & HOTKEY_ALT)
        and shift_down == bool(modifiers & HOTKEY_SHIFT)
        and win_down == bool(modifiers & HOTKEY_WIN)
    )


class HotkeyMonitor(threading.Thread):
    def __init__(
        self,
        bridge,
        virtual_key,
        modifiers,
        key_state_reader=None,
    ):
        super().__init__(name="FleeceHotkeys", daemon=True)
        virtual_key, modifiers = normalize_hotkey(virtual_key, modifiers)
        self.bridge = bridge
        self._closing = threading.Event()
        self._lock = threading.Lock()
        self._virtual_key = virtual_key
        self._modifiers = modifiers
        self._ignore_until_released = True
        self._enabled = True
        self._active_stop_event = None
        self._key_state_reader = key_state_reader

    def set_hotkey(self, virtual_key, modifiers):
        virtual_key, modifiers = normalize_hotkey(virtual_key, modifiers)
        with self._lock:
            self._virtual_key = virtual_key
            self._modifiers = modifiers
            self._ignore_until_released = True

    def set_enabled(self, enabled):
        with self._lock:
            self._enabled = bool(enabled)
            self._ignore_until_released = True

    def set_active_stop_event(self, stop_event):
        with self._lock:
            self._active_stop_event = stop_event

    def close(self):
        self._closing.set()

    def run(self):
        get_async_key_state = self._key_state_reader
        if get_async_key_state is None:
            if os.name != "nt":
                return
            user32 = ctypes.windll.user32
            user32.GetAsyncKeyState.argtypes = (ctypes.c_int,)
            user32.GetAsyncKeyState.restype = ctypes.c_short
            get_async_key_state = user32.GetAsyncKeyState

        def key_down(virtual_key):
            return bool(get_async_key_state(virtual_key) & 0x8000)

        previous_toggle = False
        previous_stop = False
        while not self._closing.wait(0.02):
            with self._lock:
                selected_vk = self._virtual_key
                selected_modifiers = self._modifiers
                ignore_until_released = self._ignore_until_released
                enabled = self._enabled
                active_stop_event = self._active_stop_event

            toggle_down = enabled and hotkey_state_matches(
                selected_vk, selected_modifiers, key_down
            )
            stop_down = key_down(EMERGENCY_VK)
            if ignore_until_released:
                if not toggle_down:
                    with self._lock:
                        self._ignore_until_released = False
                previous_toggle = toggle_down
            elif toggle_down and not previous_toggle:
                self.bridge.toggle_requested.emit()
            if stop_down:
                if active_stop_event is not None:
                    active_stop_event.set()
                if not previous_stop:
                    self.bridge.stop_requested.emit()
            previous_toggle = toggle_down
            previous_stop = stop_down


class TrafficLightButton(QPushButton):
    def __init__(self, color_name, tooltip, parent=None):
        super().__init__(parent)
        self.setObjectName(color_name)
        self.setToolTip(tooltip)
        self.setAccessibleName(tooltip)
        self.setAccessibleDescription(f"{tooltip} the current window.")
        self.setFixedSize(13, 13)
        self.setCursor(Qt.PointingHandCursor)


class TitleBar(QFrame):
    def __init__(self, host, title=APP_NAME, close_only=False):
        super().__init__(host)
        self.host = host
        self.drag_offset = QPoint()
        self.setObjectName("titleBar")
        self.setFixedHeight(38)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(8)

        close_button = TrafficLightButton("closeDot", "Close")
        close_button.clicked.connect(host.close)
        controls = QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(8)
        controls.addStretch()
        if not close_only:
            maximize = TrafficLightButton("maximizeDot", "Maximize")
            minimize = TrafficLightButton("minimizeDot", "Minimize")
            maximize.clicked.connect(self.toggle_maximized)
            minimize.clicked.connect(host.showMinimized)
            controls.addWidget(maximize)
            controls.addWidget(minimize)
        controls.addWidget(close_button)
        controls_holder = QWidget()
        controls_holder.setFixedWidth(64 if not close_only else 13)
        controls_holder.setLayout(controls)

        title_label = QLabel(title)
        title_label.setObjectName("windowTitle")
        title_label.setAccessibleName(f"{title} window title")
        title_label.setAlignment(Qt.AlignCenter)
        left_spacer = QWidget()
        left_spacer.setFixedWidth(controls_holder.width())
        layout.addWidget(left_spacer)
        layout.addStretch()
        layout.addWidget(title_label)
        layout.addStretch()
        layout.addWidget(controls_holder)

    def toggle_maximized(self):
        self.host.showNormal() if self.host.isMaximized() else self.host.showMaximized()

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.toggle_maximized()
            event.accept()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.drag_offset = event.globalPosition().toPoint() - self.host.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() & Qt.LeftButton and not self.host.isMaximized():
            self.host.move(event.globalPosition().toPoint() - self.drag_offset)
            event.accept()


class ChevronButton(QPushButton):
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(Qt.white, 1.4))
        x = self.width() - 20
        y = self.height() // 2 - 1
        painter.drawLine(x - 4, y - 2, x, y + 2)
        painter.drawLine(x, y + 2, x + 4, y - 2)


def qt_key_to_virtual_key(event):
    native_key = int(event.nativeVirtualKey())
    if native_key:
        return native_key

    key = int(event.key())
    if ord("0") <= key <= ord("9") or ord("A") <= key <= ord("Z"):
        return key
    if int(Qt.Key_F1) <= key <= int(Qt.Key_F24):
        return 0x70 + key - int(Qt.Key_F1)
    special_keys = {
        int(Qt.Key_Backspace): 0x08,
        int(Qt.Key_Tab): 0x09,
        int(Qt.Key_Return): 0x0D,
        int(Qt.Key_Enter): 0x0D,
        int(Qt.Key_Pause): 0x13,
        int(Qt.Key_Escape): 0x1B,
        int(Qt.Key_Space): 0x20,
        int(Qt.Key_PageUp): 0x21,
        int(Qt.Key_PageDown): 0x22,
        int(Qt.Key_End): 0x23,
        int(Qt.Key_Home): 0x24,
        int(Qt.Key_Left): 0x25,
        int(Qt.Key_Up): 0x26,
        int(Qt.Key_Right): 0x27,
        int(Qt.Key_Down): 0x28,
        int(Qt.Key_Print): 0x2C,
        int(Qt.Key_Insert): 0x2D,
        int(Qt.Key_Delete): 0x2E,
    }
    return special_keys.get(key, 0)


def qt_modifiers_to_hotkey_mask(modifiers):
    mask = 0
    if modifiers & Qt.ControlModifier:
        mask |= HOTKEY_CTRL
    if modifiers & Qt.AltModifier:
        mask |= HOTKEY_ALT
    if modifiers & Qt.ShiftModifier:
        mask |= HOTKEY_SHIFT
    if modifiers & Qt.MetaModifier:
        mask |= HOTKEY_WIN
    return mask


def hotkey_display_text(key, modifiers):
    key, modifiers = normalize_hotkey(key, modifiers)
    if 0x70 <= key <= 0x87:
        key_text = f"F{key - 0x6F}"
    elif 0x60 <= key <= 0x69:
        key_text = f"Numpad {key - 0x60}"
    elif ord("0") <= key <= ord("9") or ord("A") <= key <= ord("Z"):
        key_text = chr(key)
    else:
        key_text = {
            0x08: "Backspace",
            0x09: "Tab",
            0x0D: "Enter",
            0x13: "Pause",
            0x1B: "Esc",
            0x20: "Space",
            0x21: "PgUp",
            0x22: "PgDown",
            0x23: "End",
            0x24: "Home",
            0x25: "Left",
            0x26: "Up",
            0x27: "Right",
            0x28: "Down",
            0x2C: "Print Screen",
            0x2D: "Insert",
            0x2E: "Delete",
            0x6A: "Numpad *",
            0x6B: "Numpad +",
            0x6C: "Numpad Separator",
            0x6D: "Numpad -",
            0x6E: "Numpad Decimal",
            0x6F: "Numpad /",
            0x90: "Num Lock",
            0x91: "Scroll Lock",
        }.get(key, f"Key 0x{key:02X}")
    parts = []
    for modifier, label in (
        (HOTKEY_CTRL, "Ctrl"),
        (HOTKEY_ALT, "Alt"),
        (HOTKEY_SHIFT, "Shift"),
        (HOTKEY_WIN, "Win"),
    ):
        if modifiers & modifier:
            parts.append(label)
    parts.append(key_text)
    return "+".join(parts)


class HotkeyCaptureButton(QPushButton):
    changed = Signal(int, int, str)
    recording_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.virtual_key = DEFAULT_HOTKEY_VK
        self.modifiers = 0
        self.display_text = "F6"
        self.recording = False
        self.setObjectName("hotkeyButton")
        self.setMinimumHeight(38)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setToolTip("Click here, then press the keyboard shortcut you want.")
        self.clicked.connect(self.begin_recording)
        self.set_hotkey(DEFAULT_HOTKEY_VK, 0, "F6")

    def set_hotkey(self, virtual_key, modifiers, display_text=None):
        self.virtual_key, self.modifiers = normalize_hotkey(
            virtual_key,
            modifiers,
        )
        self.display_text = hotkey_display_text(self.virtual_key, self.modifiers)
        if not self.recording:
            self.setText(self.display_text)
        self.setAccessibleName(
            f"Start and stop keyboard shortcut: {self.display_text}"
        )

    def begin_recording(self):
        if self.recording:
            return
        self.recording = True
        self.setText("Press your new shortcut...")
        self.setFocus(Qt.ShortcutFocusReason)
        self.recording_changed.emit(True)

    def cancel_recording(self):
        if not self.recording:
            return
        self.recording = False
        self.setText(self.display_text)
        self.recording_changed.emit(False)

    def keyPressEvent(self, event):
        if not self.recording:
            super().keyPressEvent(event)
            return
        if event.isAutoRepeat():
            event.accept()
            return

        key = int(event.key())
        pure_modifiers = {
            int(Qt.Key_Shift),
            int(Qt.Key_Control),
            int(Qt.Key_Alt),
            int(Qt.Key_Meta),
            int(Qt.Key_AltGr),
        }
        if key in pure_modifiers:
            self.setText("Keep holding it and press another key...")
            event.accept()
            return

        modifiers = qt_modifiers_to_hotkey_mask(event.modifiers())
        if key == int(Qt.Key_Escape) and modifiers == 0:
            self.cancel_recording()
            event.accept()
            return

        virtual_key = qt_key_to_virtual_key(event)
        if virtual_key == EMERGENCY_VK:
            self.setText("F8 always stops - choose another key")
            event.accept()
            return
        normalized_key, normalized_modifiers = normalize_hotkey(
            virtual_key,
            modifiers,
        )
        if (normalized_key, normalized_modifiers) != (virtual_key, modifiers):
            self.setText("That key is unsupported - try another")
            event.accept()
            return

        display_text = hotkey_display_text(virtual_key, modifiers)

        self.recording = False
        self.set_hotkey(virtual_key, modifiers, display_text)
        self.changed.emit(virtual_key, modifiers, display_text)
        self.recording_changed.emit(False)
        event.accept()

    def focusOutEvent(self, event):
        if self.recording:
            self.cancel_recording()
        super().focusOutEvent(event)


class AnimatedDropdown(QWidget):
    changed = Signal(str)

    def __init__(self, items, parent=None):
        super().__init__(parent)
        self.items = list(items)
        self._current = self.items[0]
        self._animation = None
        self._hide_after_animation = False
        self._closing = False
        self._restore_focus_after_hide = False
        self._app_filter_installed = False
        self._host_window = None
        self.option_buttons = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.button = ChevronButton(self._current)
        self.button.setObjectName("dropdownButton")
        self.button.setMinimumHeight(38)
        self.button.setAccessibleName("Choose an option")
        self.button.clicked.connect(self.toggle_popup)
        layout.addWidget(self.button)

        self.popup = QFrame(
            self,
            Qt.Tool | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint,
        )
        self.popup.setObjectName("dropdownPopup")
        self.popup.setAttribute(Qt.WA_TranslucentBackground)
        outer = QVBoxLayout(self.popup)
        outer.setContentsMargins(0, 0, 0, 0)
        surface = QFrame()
        surface.setObjectName("dropdownSurface")
        surface_layout = QVBoxLayout(surface)
        surface_layout.setContentsMargins(5, 5, 5, 5)
        surface_layout.setSpacing(2)
        for item in self.items:
            option = QPushButton(item)
            option.setObjectName("dropdownOption")
            option.setMinimumHeight(32)
            option.setCheckable(True)
            option.setAccessibleName(item)
            option.installEventFilter(self)
            option.clicked.connect(lambda checked=False, value=item: self.select(value))
            surface_layout.addWidget(option)
            self.option_buttons.append(option)
        outer.addWidget(surface)
        self.button.installEventFilter(self)
        self._sync_selected_state()

    def currentText(self):
        return self._current

    def setCurrentText(self, value, emit=False):
        if value not in self.items:
            value = self.items[0]
        self._current = value
        self.button.setText(value)
        self._sync_selected_state()
        if emit:
            self.changed.emit(value)

    def select(self, value):
        self.setCurrentText(value, emit=True)
        self.hide_popup(restore_focus=True)

    def toggle_popup(self):
        if self.popup.isVisible() and not self._closing:
            self.hide_popup()
        else:
            self.show_popup()

    def show_popup(self, focus_index=None):
        if not self.isEnabled() or not self.items:
            return
        self._stop_popup_animation()
        self._closing = False
        self._restore_focus_after_hide = False
        self._ensure_host_event_filter()
        self._install_app_filter()
        self.popup.setGeometry(self._popup_geometry())
        self.popup.setWindowOpacity(0.0)
        self.popup.show()
        self.popup.raise_()
        self._start_popup_animation(0.0, 1.0, 110, QEasingCurve.OutCubic, False)
        if focus_index is not None:
            QTimer.singleShot(0, lambda: self._focus_option(focus_index))

    def hide_popup(self, restore_focus=False, immediate=False):
        if not self.popup.isVisible():
            self._remove_app_filter()
            if restore_focus:
                self._restore_button_focus()
            return
        self._stop_popup_animation()
        self._restore_focus_after_hide = bool(restore_focus)
        self._remove_app_filter()
        if immediate:
            self.popup.hide()
            self.popup.setWindowOpacity(1.0)
            self._closing = False
            self._hide_after_animation = False
            if self._restore_focus_after_hide:
                self._restore_button_focus()
            self._restore_focus_after_hide = False
            return
        self._closing = True
        self._start_popup_animation(
            self.popup.windowOpacity(),
            0.0,
            75,
            QEasingCurve.InCubic,
            True,
        )

    def _start_popup_animation(
        self,
        start_opacity,
        end_opacity,
        duration,
        easing,
        hide_after,
    ):
        if self._animation is None:
            self._animation = QPropertyAnimation(
                self.popup,
                b"windowOpacity",
                self,
            )
            self._animation.finished.connect(self._popup_animation_finished)
        self._hide_after_animation = hide_after
        self._animation.setDuration(duration)
        self._animation.setStartValue(start_opacity)
        self._animation.setEndValue(end_opacity)
        self._animation.setEasingCurve(easing)
        self._animation.start()

    def _stop_popup_animation(self):
        if self._animation is None:
            return
        self._animation.stop()

    def _popup_animation_finished(self):
        if self._hide_after_animation:
            self.popup.hide()
            self.popup.setWindowOpacity(1.0)
            self._closing = False
            if self._restore_focus_after_hide:
                self._restore_button_focus()
        self._hide_after_animation = False
        self._restore_focus_after_hide = False

    def _sync_selected_state(self):
        self.button.setAccessibleDescription(f"Current choice: {self._current}")
        for item, option in zip(self.items, self.option_buttons):
            selected = item == self._current
            option.setChecked(selected)
            option.setProperty("selected", selected)
            option.setAccessibleDescription(
                "Selected choice" if selected else "Available choice"
            )

    def _ensure_host_event_filter(self):
        host_window = self.window()
        if host_window is self._host_window:
            return
        if self._host_window is not None:
            self._host_window.removeEventFilter(self)
        self._host_window = host_window
        if self._host_window is not None:
            self._host_window.installEventFilter(self)

    def _install_app_filter(self):
        application = QApplication.instance()
        if application is not None and not self._app_filter_installed:
            application.installEventFilter(self)
            self._app_filter_installed = True

    def _remove_app_filter(self):
        application = QApplication.instance()
        if application is not None and self._app_filter_installed:
            application.removeEventFilter(self)
        self._app_filter_installed = False

    def _popup_geometry(self):
        popup_height = len(self.items) * 34 + 12
        button_top_left = self.button.mapToGlobal(QPoint(0, 0))
        button_rect = QRect(button_top_left, self.button.size())
        screen = QApplication.screenAt(button_rect.center())
        if screen is None:
            screen = QApplication.primaryScreen()
        available = screen.availableGeometry() if screen is not None else QRect()
        popup_width = max(1, self.width())
        if not available.isValid():
            return QRect(
                button_rect.left(),
                button_rect.bottom() + 5,
                popup_width,
                popup_height,
            )

        popup_width = min(popup_width, available.width())
        popup_height = min(popup_height, available.height())
        max_x = available.right() - popup_width + 1
        final_x = min(max(button_rect.left(), available.left()), max_x)
        below_y = button_rect.bottom() + 5
        above_y = button_rect.top() - popup_height - 4
        if below_y + popup_height - 1 <= available.bottom():
            final_y = below_y
        elif above_y >= available.top():
            final_y = above_y
        else:
            final_y = min(
                max(below_y, available.top()),
                available.bottom() - popup_height + 1,
            )
        final_y = min(
            max(final_y, available.top()),
            available.bottom() - popup_height + 1,
        )
        return QRect(final_x, final_y, popup_width, popup_height)

    def _reposition_popup(self):
        if self.popup.isVisible() and not self._closing:
            self.popup.setGeometry(self._popup_geometry())

    def _focus_option(self, index):
        if not self.popup.isVisible() or not self.option_buttons:
            return
        index = max(0, min(int(index), len(self.option_buttons) - 1))
        self.option_buttons[index].setFocus(Qt.PopupFocusReason)

    def _restore_button_focus(self):
        if self.button.isVisible() and self.button.isEnabled():
            if self._host_window is not None and self._host_window.isVisible():
                self._host_window.activateWindow()
            self.button.setFocus(Qt.PopupFocusReason)
            QTimer.singleShot(
                0,
                lambda: self.button.setFocus(Qt.PopupFocusReason),
            )

    def _current_index(self):
        try:
            return self.items.index(self._current)
        except ValueError:
            return 0

    def _handle_keyboard_event(self, watched, event):
        if event.type() != QEvent.KeyPress or event.isAutoRepeat():
            return False
        key = int(event.key())
        option_index = (
            self.option_buttons.index(watched)
            if watched in self.option_buttons
            else None
        )
        if key == int(Qt.Key_Escape) and self.popup.isVisible():
            self.hide_popup(restore_focus=True)
            event.accept()
            return True

        navigation_keys = {
            int(Qt.Key_Up),
            int(Qt.Key_Down),
            int(Qt.Key_Home),
            int(Qt.Key_End),
        }
        activation_keys = {
            int(Qt.Key_Enter),
            int(Qt.Key_Return),
            int(Qt.Key_Space),
        }
        if watched is self.button:
            if key in navigation_keys or key in activation_keys:
                current_index = self._current_index()
                if key == int(Qt.Key_Home):
                    current_index = 0
                elif key == int(Qt.Key_End):
                    current_index = len(self.option_buttons) - 1
                self.show_popup(focus_index=current_index)
                event.accept()
                return True
            return False

        if option_index is None:
            return False
        if key == int(Qt.Key_Up):
            self._focus_option((option_index - 1) % len(self.option_buttons))
        elif key == int(Qt.Key_Down):
            self._focus_option((option_index + 1) % len(self.option_buttons))
        elif key == int(Qt.Key_Home):
            self._focus_option(0)
        elif key == int(Qt.Key_End):
            self._focus_option(len(self.option_buttons) - 1)
        elif key in activation_keys:
            self.select(self.items[option_index])
        else:
            return False
        event.accept()
        return True

    def _close_if_host_inactive(self):
        if not self.popup.isVisible():
            return
        active_window = QApplication.activeWindow()
        if active_window not in (self._host_window, self.popup):
            self.hide_popup(immediate=True)

    def eventFilter(self, watched, event):
        if watched is self.button or watched in self.option_buttons:
            if self._handle_keyboard_event(watched, event):
                return True

        event_type = event.type()
        if (
            self.popup.isVisible()
            and event_type == QEvent.KeyPress
            and int(event.key()) == int(Qt.Key_Escape)
        ):
            self.hide_popup(restore_focus=True)
            event.accept()
            return True
        if watched is self._host_window and self.popup.isVisible():
            if event_type in (QEvent.Move, QEvent.Resize):
                self._reposition_popup()
                QTimer.singleShot(0, self._reposition_popup)
            elif event_type in (
                QEvent.WindowStateChange,
                QEvent.Hide,
                QEvent.Close,
            ):
                self.hide_popup(immediate=True)
            elif event_type == QEvent.WindowDeactivate:
                QTimer.singleShot(0, self._close_if_host_inactive)

        application = QApplication.instance()
        if (
            watched is application
            and self.popup.isVisible()
            and event_type == QEvent.ApplicationDeactivate
        ):
            self.hide_popup(immediate=True)
        elif self.popup.isVisible() and event_type == QEvent.MouseButtonPress:
            point = event.globalPosition().toPoint()
            button_rect = QRect(self.button.mapToGlobal(QPoint(0, 0)), self.button.size())
            if not self.popup.frameGeometry().contains(point) and not button_rect.contains(point):
                self.hide_popup(immediate=True)
        return super().eventFilter(watched, event)

    def changeEvent(self, event):
        if (
            event.type() == QEvent.EnabledChange
            and hasattr(self, "popup")
            and not self.isEnabled()
        ):
            self.hide_popup(immediate=True)
        super().changeEvent(event)

    def hideEvent(self, event):
        if hasattr(self, "popup"):
            self.hide_popup(immediate=True)
        super().hideEvent(event)


APP_STYLE = """
QWidget { color: #f5f5f5; font-family: "Segoe UI"; font-size: 13px; }
QFrame#windowFrame { background: #070707; border: 1px solid #252525; border-radius: 14px; }
QFrame#titleBar { background: #070707; border: none; border-bottom: 1px solid #1c1c1c; border-top-left-radius: 14px; border-top-right-radius: 14px; }
QLabel#windowTitle { color: #bdbdbd; font-size: 12px; font-weight: 600; }
QPushButton#closeDot, QPushButton#minimizeDot, QPushButton#maximizeDot { border: none; border-radius: 6px; min-height: 13px; max-height: 13px; min-width: 13px; max-width: 13px; padding: 0; }
QPushButton#closeDot { background: #ff5f57; }
QPushButton#minimizeDot { background: #febc2e; }
QPushButton#maximizeDot { background: #28c840; }
QPushButton#closeDot:hover, QPushButton#minimizeDot:hover, QPushButton#maximizeDot:hover { border: 1px solid rgba(0, 0, 0, 90); }
QLabel#label { color: #b8b8b8; font-size: 12px; font-weight: 600; }
QLabel#status { color: #8b8b8b; font-size: 12px; }
QLabel#note { color: #7a7a7a; font-size: 11px; }
QLabel#count { color: #8b8b8b; font-size: 11px; }
QFrame#panel { background: #0d0d0d; border: 1px solid #242424; border-radius: 14px; }
QLineEdit { background: #0a0a0a; border: 1px solid #292929; border-radius: 10px; min-height: 36px; padding: 0 12px; selection-background-color: #ffffff; selection-color: #000000; }
QLineEdit:focus { border: 1px solid #ffffff; }
QLineEdit:disabled { color: #555555; background: #090909; }
QPushButton { background: #151515; border: 1px solid #2b2b2b; border-radius: 10px; min-height: 36px; padding: 0 14px; font-weight: 600; }
QPushButton:hover { background: #1d1d1d; border-color: #3a3a3a; }
QPushButton:pressed { background: #101010; }
QPushButton:disabled { color: #555555; background: #101010; border-color: #1d1d1d; }
QPushButton#primary { background: #ffffff; color: #000000; border: none; min-height: 42px; }
QPushButton#primary:hover { background: #e7e7e7; }
QPushButton#danger { background: #6e1c1c; color: #ffffff; border: 1px solid #9a2929; min-height: 42px; }
QPushButton#danger:hover { background: #852323; }
QPushButton#small { min-height: 28px; max-height: 28px; border-radius: 8px; padding: 0 10px; color: #bdbdbd; font-size: 11px; }
QPushButton#dropdownButton { background: #0a0a0a; border: 1px solid #292929; border-radius: 10px; min-height: 36px; padding: 0 38px 0 12px; text-align: left; font-weight: 500; }
QPushButton#dropdownButton:hover { background: #101010; border-color: #3b3b3b; }
QFrame#dropdownSurface { background: #111111; border: 1px solid #303030; border-radius: 11px; }
QPushButton#dropdownOption { background: transparent; border: none; border-radius: 7px; min-height: 32px; padding: 0 10px; text-align: left; font-weight: 500; }
QPushButton#dropdownOption:hover { background: #242424; }
QPushButton#dropdownOption:checked { background: #1b1b1b; }
QScrollArea#contentScroll { background: transparent; border: none; }
QScrollArea#contentScroll > QWidget > QWidget { background: transparent; }
QTextEdit { background: #090909; color: #c8c8c8; border: 1px solid #242424; border-radius: 10px; padding: 8px; font-family: "Cascadia Mono", "Consolas"; font-size: 11px; selection-background-color: #ffffff; selection-color: #000000; }
QCheckBox { color: #b8b8b8; spacing: 8px; }
QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #343434; border-radius: 5px; background: #0a0a0a; }
QCheckBox::indicator:checked { background: #ffffff; border-color: #ffffff; }
QCheckBox::indicator:disabled { background: #111111; border-color: #252525; }
QScrollBar:vertical { width: 8px; background: transparent; }
QScrollBar::handle:vertical { background: #333333; border-radius: 4px; min-height: 24px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""


class SafetyWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.Window | Qt.FramelessWindowHint)
        self.setWindowTitle("Shortcuts & safety")
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(470, 390)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        frame = QFrame()
        frame.setObjectName("windowFrame")
        outer.addWidget(frame)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(TitleBar(self, "Shortcuts & safety", close_only=True))
        content = QVBoxLayout()
        content.setContentsMargins(22, 20, 22, 22)
        content.setSpacing(12)
        heading = QLabel("Stay in control")
        heading.setObjectName("label")
        content.addWidget(heading)
        body = QLabel(
            "• Your selected keyboard shortcut starts or stops clicking anywhere.\n\n"
            "• F8 is always the emergency stop, including during the start delay.\n\n"
            "• A saved spot moves the pointer back before every click.\n\n"
            "• Windows may keep shortcuts that are already used by the system or another app.\n\n"
            "• Closing the app stops the worker before the window exits.\n\n"
            "Use automation only where it is allowed and keep an emergency stop key available."
        )
        body.setWordWrap(True)
        body.setObjectName("status")
        content.addWidget(body)
        content.addStretch()
        version = QLabel(f"Auto Clicker v{APP_VERSION} • local only")
        version.setObjectName("note")
        content.addWidget(version)
        layout.addLayout(content, 1)


class AutoClicker(QMainWindow):
    def __init__(self, testing=False, settings_path=None):
        super().__init__()
        self.testing = testing
        self.setWindowTitle(APP_NAME)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(680, 748)
        self.setMinimumSize(360, 320)

        self.runtime_error = ""
        try:
            RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            self.runtime_error = str(error)
        self.settings = QSettings(str(settings_path or SETTINGS_PATH), QSettings.IniFormat)
        self._settings_sync_timer = QTimer(self)
        self._settings_sync_timer.setSingleShot(True)
        self._settings_sync_timer.setInterval(150)
        self._settings_sync_timer.timeout.connect(self.settings.sync)
        self.mouse = None if testing else WindowsMouseController()
        self.bridge = UiBridge()
        self.bridge.toggle_requested.connect(self.start_or_stop)
        self.bridge.stop_requested.connect(self.stop_clicking)
        self.bridge.count_changed.connect(self.update_count)
        self.bridge.status_changed.connect(self.status_label_text)
        self.bridge.job_finished.connect(self.job_finished)
        self.worker_thread = None
        self.worker_stop = None
        self.running = False
        self.action_count = 0
        self.active_click_type = CLICK_ONCE
        self.hotkey_monitor = None
        self.safety_window = None

        QApplication.instance().setStyleSheet(APP_STYLE)
        self.build_ui()
        self.restore_preferences()
        self.sync_dynamic_controls()
        if self.runtime_error:
            self.start_button.setEnabled(False)
            self.status_label.setText("Local storage is unavailable")
            self.append_log("Run Installer.bat again from a writable folder.")
        elif not testing:
            self.hotkey_monitor = HotkeyMonitor(
                self.bridge,
                self.hotkey_button.virtual_key,
                self.hotkey_button.modifiers,
            )
            self.hotkey_monitor.start()
            self.append_log("Ready. F8 is always the emergency stop.")

    def build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        window_frame = QFrame()
        window_frame.setObjectName("windowFrame")
        outer.addWidget(window_frame)
        window_layout = QVBoxLayout(window_frame)
        window_layout.setContentsMargins(0, 0, 0, 0)
        window_layout.setSpacing(0)
        window_layout.addWidget(TitleBar(self))

        content = QWidget()
        content.setObjectName("scrollContent")
        content.setMinimumSize(638, 708)
        self.content_scroll = QScrollArea()
        self.content_scroll.setObjectName("contentScroll")
        self.content_scroll.setFrameShape(QFrame.NoFrame)
        self.content_scroll.setWidgetResizable(True)
        self.content_scroll.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.content_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.content_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.content_scroll.setFocusPolicy(Qt.NoFocus)
        self.content_scroll.setWidget(content)
        window_layout.addWidget(self.content_scroll, 1)
        page = QVBoxLayout(content)
        page.setContentsMargins(22, 14, 22, 14)
        panel = QFrame()
        panel.setObjectName("panel")
        panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        page.addWidget(panel, 1)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(7)

        timing_row = QHBoxLayout()
        timing_row.setSpacing(10)
        timing_mode_column = self.control_column("Choose the speed by", timing_row)
        self.rate_dropdown = AnimatedDropdown([RATE_CPS, RATE_DELAY])
        self.rate_dropdown.button.setAccessibleName("Choose the speed by")
        self.rate_dropdown.changed.connect(self.timing_changed)
        timing_mode_column.addWidget(self.rate_dropdown)
        rate_column = self.control_column("Clicks per second", timing_row)
        self.rate_value_label = rate_column.itemAt(0).widget()
        self.rate_input = QLineEdit("10")
        self.rate_input.setPlaceholderText("10")
        self.rate_input.setToolTip(
            "For example, 10 means the app clicks ten times every second."
        )
        self.rate_value_label.setBuddy(self.rate_input)
        self.rate_input.setAccessibleName("Clicks per second")
        self.rate_input.editingFinished.connect(self.rate_editing_finished)
        rate_column.addWidget(self.rate_input)
        layout.addLayout(timing_row)

        click_row = QHBoxLayout()
        click_row.setSpacing(10)
        button_column = self.control_column("Mouse button", click_row)
        self.button_dropdown = AnimatedDropdown(["Left", "Right", "Middle"])
        self.button_dropdown.button.setAccessibleName("Mouse button")
        self.button_dropdown.changed.connect(self.save_preferences)
        button_column.addWidget(self.button_dropdown)
        type_column = self.control_column("What one click should do", click_row)
        self.type_dropdown = AnimatedDropdown([CLICK_ONCE, CLICK_DOUBLE])
        self.type_dropdown.button.setAccessibleName("What one click should do")
        self.type_dropdown.changed.connect(self.click_type_changed)
        type_column.addWidget(self.type_dropdown)
        layout.addLayout(click_row)

        repeat_row = QHBoxLayout()
        repeat_row.setSpacing(10)
        repeat_column = self.control_column("Stop clicking", repeat_row)
        self.repeat_dropdown = AnimatedDropdown(
            [REPEAT_MANUAL, REPEAT_COUNT, REPEAT_SECONDS]
        )
        self.repeat_dropdown.button.setAccessibleName("Stop clicking")
        self.repeat_dropdown.changed.connect(self.repeat_changed)
        repeat_column.addWidget(self.repeat_dropdown)
        repeat_value_column = self.control_column("Not needed", repeat_row)
        self.repeat_value_label = repeat_value_column.itemAt(0).widget()
        self.repeat_input = QLineEdit("100")
        self.repeat_input.setPlaceholderText("Not used")
        self.repeat_value_label.setBuddy(self.repeat_input)
        self.repeat_input.setAccessibleName("Repeat value")
        self.repeat_input.editingFinished.connect(self.save_preferences)
        repeat_value_column.addWidget(self.repeat_input)
        layout.addLayout(repeat_row)

        detail_row = QHBoxLayout()
        detail_row.setSpacing(10)
        delay_column = self.control_column("Wait before starting (seconds)", detail_row)
        self.delay_label = delay_column.itemAt(0).widget()
        self.delay_input = QLineEdit("3")
        self.delay_input.setPlaceholderText("0")
        self.delay_label.setBuddy(self.delay_input)
        self.delay_input.setAccessibleName("Wait before starting in seconds")
        self.delay_input.editingFinished.connect(self.save_preferences)
        delay_column.addWidget(self.delay_input)
        variation_column = self.control_column("Random timing (0 = off)", detail_row)
        self.variation_label = variation_column.itemAt(0).widget()
        self.variation_input = QLineEdit("0")
        self.variation_input.setPlaceholderText("0")
        self.variation_label.setBuddy(self.variation_input)
        self.variation_input.setAccessibleName("Random timing percent, 0 turns it off")
        self.variation_input.setToolTip(
            "0 keeps every delay the same. A higher number changes each delay "
            "slightly so the timing is less exact."
        )
        self.variation_input.editingFinished.connect(self.save_preferences)
        variation_column.addWidget(self.variation_input)
        layout.addLayout(detail_row)

        target_row = QHBoxLayout()
        target_row.setSpacing(10)
        target_column = self.control_column("Where to click", target_row)
        self.target_dropdown = AnimatedDropdown([TARGET_CURSOR, TARGET_FIXED])
        self.target_dropdown.button.setAccessibleName("Where to click")
        self.target_dropdown.changed.connect(self.target_changed)
        target_column.addWidget(self.target_dropdown)
        position_column = self.control_column("Saved screen position", target_row)
        self.position_label = position_column.itemAt(0).widget()
        position_row = QHBoxLayout()
        position_row.setSpacing(7)
        self.x_input = QLineEdit("0")
        self.x_input.setPlaceholderText("X")
        self.x_input.setFixedWidth(72)
        self.x_input.setAccessibleName("Saved screen X position")
        self.x_input.editingFinished.connect(self.save_preferences)
        self.y_input = QLineEdit("0")
        self.y_input.setPlaceholderText("Y")
        self.y_input.setFixedWidth(72)
        self.y_input.setAccessibleName("Saved screen Y position")
        self.y_input.editingFinished.connect(self.save_preferences)
        self.capture_button = QPushButton("Use cursor position")
        self.position_label.setBuddy(self.x_input)
        self.capture_button.clicked.connect(self.capture_position)
        position_row.addWidget(self.x_input)
        position_row.addWidget(self.y_input)
        position_row.addWidget(self.capture_button, 1)
        position_column.addLayout(position_row)
        layout.addLayout(target_row)

        hotkey_row = QHBoxLayout()
        hotkey_row.setSpacing(10)
        hotkey_column = self.control_column(
            "Start / stop keyboard shortcut", hotkey_row
        )
        self.hotkey_button = HotkeyCaptureButton()
        self.hotkey_button.changed.connect(self.hotkey_changed)
        self.hotkey_button.recording_changed.connect(self.hotkey_recording_changed)
        hotkey_column.addWidget(self.hotkey_button)
        preference_column = self.control_column("Keep the app visible", hotkey_row)
        checkbox_holder = QFrame()
        checkbox_holder.setObjectName("checkboxHolder")
        checkbox_layout = QHBoxLayout(checkbox_holder)
        checkbox_layout.setContentsMargins(1, 0, 0, 0)
        self.topmost_checkbox = QCheckBox("Keep window on top")
        self.topmost_checkbox.toggled.connect(self.topmost_changed)
        checkbox_layout.addWidget(self.topmost_checkbox)
        checkbox_layout.addStretch()
        preference_column.addWidget(checkbox_holder)
        layout.addLayout(hotkey_row)

        self.hotkey_note = QLabel(
            "Click the shortcut box, then press any key combination • F8 always stops"
        )
        self.hotkey_note.setObjectName("note")
        layout.addWidget(self.hotkey_note)

        self.start_button = QPushButton("Start clicking (F6)")
        self.start_button.setObjectName("primary")
        self.start_button.clicked.connect(self.start_or_stop)
        layout.addWidget(self.start_button)

        status_row = QHBoxLayout()
        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("status")
        self.count_label = QLabel("0 completed")
        self.count_label.setObjectName("count")
        status_row.addWidget(self.status_label)
        status_row.addStretch()
        status_row.addWidget(self.count_label)
        layout.addLayout(status_row)

        log_header = QHBoxLayout()
        log_label = QLabel("Log")
        log_label.setObjectName("label")
        safety_button = QPushButton("Shortcuts & safety")
        safety_button.setObjectName("small")
        safety_button.clicked.connect(self.open_safety)
        clear_button = QPushButton("Clear")
        clear_button.setObjectName("small")
        clear_button.clicked.connect(self.clear_log)
        log_header.addWidget(log_label)
        log_header.addStretch()
        log_header.addWidget(safety_button)
        log_header.addWidget(clear_button)
        layout.addLayout(log_header)
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.document().setMaximumBlockCount(500)
        self.log_box.setPlaceholderText("No activity")
        self.log_box.setMinimumHeight(72)
        layout.addWidget(self.log_box, 1)

    @staticmethod
    def control_column(label_text, parent_row):
        column = QVBoxLayout()
        column.setSpacing(6)
        label = QLabel(label_text)
        label.setObjectName("label")
        column.addWidget(label)
        parent_row.addLayout(column, 1)
        return column

    def setting_text(self, key, default):
        value = self.settings.value(key, default)
        return str(default if value is None else value)

    def setting_bool(self, key, default=False):
        value = str(self.settings.value(key, "true" if default else "false")).lower()
        return value in ("1", "true", "yes", "on")

    def setting_int(self, key, default):
        try:
            return int(self.settings.value(key, default))
        except (TypeError, ValueError):
            return int(default)

    def restore_preferences(self):
        rate_mode = self.setting_text("rate_mode", RATE_CPS)
        if rate_mode == "Interval (milliseconds)":
            rate_mode = RATE_DELAY
        self.rate_dropdown.setCurrentText(rate_mode)
        self.rate_input.setText(self.setting_text("rate_value", "10"))
        self.button_dropdown.setCurrentText(self.setting_text("button", "Left"))
        click_type = self.setting_text("click_type", CLICK_ONCE)
        self.type_dropdown.setCurrentText(
            {"Single": CLICK_ONCE, "Double": CLICK_DOUBLE}.get(
                click_type, click_type
            )
        )
        repeat_mode = self.setting_text("repeat_mode", REPEAT_MANUAL)
        self.repeat_dropdown.setCurrentText(
            {
                "Until stopped": REPEAT_MANUAL,
                "Click count": REPEAT_COUNT,
                "Duration (seconds)": REPEAT_SECONDS,
            }.get(repeat_mode, repeat_mode)
        )
        self.repeat_input.setText(self.setting_text("repeat_value", "100"))
        self.delay_input.setText(self.setting_text("start_delay", "3"))
        self.variation_input.setText(self.setting_text("variation_percent", "0"))
        target_mode = self.setting_text("target_mode", TARGET_CURSOR)
        self.target_dropdown.setCurrentText(
            {
                "Current cursor": TARGET_CURSOR,
                "Fixed position": TARGET_FIXED,
            }.get(target_mode, target_mode)
        )
        self.x_input.setText(self.setting_text("target_x", "0"))
        self.y_input.setText(self.setting_text("target_y", "0"))
        legacy_hotkey = self.setting_text("hotkey", "F6")
        virtual_key = self.setting_int(
            "hotkey_vk",
            LEGACY_HOTKEYS.get(legacy_hotkey, DEFAULT_HOTKEY_VK),
        )
        modifiers = self.setting_int("hotkey_modifiers", 0)
        virtual_key, modifiers = normalize_hotkey(virtual_key, modifiers)
        self.hotkey_button.set_hotkey(virtual_key, modifiers)
        self.update_hotkey_text()
        signals_were_blocked = self.topmost_checkbox.blockSignals(True)
        self.topmost_checkbox.setChecked(self.setting_bool("topmost", False))
        self.topmost_checkbox.blockSignals(signals_were_blocked)
        self.enforce_rate_limit(notify=False)

    def save_preferences(self, value=None):
        self.settings.setValue("rate_mode", self.rate_dropdown.currentText())
        self.settings.setValue("rate_value", self.rate_input.text().strip())
        self.settings.setValue("button", self.button_dropdown.currentText())
        self.settings.setValue("click_type", self.type_dropdown.currentText())
        self.settings.setValue("repeat_mode", self.repeat_dropdown.currentText())
        self.settings.setValue("repeat_value", self.repeat_input.text().strip())
        self.settings.setValue("start_delay", self.delay_input.text().strip())
        self.settings.setValue("variation_percent", self.variation_input.text().strip())
        self.settings.setValue("target_mode", self.target_dropdown.currentText())
        self.settings.setValue("target_x", self.x_input.text().strip())
        self.settings.setValue("target_y", self.y_input.text().strip())
        self.settings.setValue("hotkey", self.hotkey_button.display_text)
        self.settings.setValue("hotkey_display", self.hotkey_button.display_text)
        self.settings.setValue("hotkey_vk", self.hotkey_button.virtual_key)
        self.settings.setValue("hotkey_modifiers", self.hotkey_button.modifiers)
        self.settings.setValue("topmost", self.topmost_checkbox.isChecked())
        self._settings_sync_timer.start()

    def timing_changed(self, value):
        if not self.rate_input.text().strip():
            self.rate_input.setText("10" if value == RATE_CPS else "100")
        self.timing_changed_ui_only()
        self.enforce_rate_limit(notify=True)
        self.save_preferences()

    def rate_editing_finished(self):
        self.enforce_rate_limit(notify=True)
        self.save_preferences()

    def click_type_changed(self, value):
        self.sync_dynamic_controls()
        self.enforce_rate_limit(notify=True)
        self.save_preferences()

    def enforce_rate_limit(self, notify=False):
        try:
            value = parse_number(self.rate_input.text(), "Click rate")
        except ValueError:
            return False

        click_type = self.type_dropdown.currentText()
        if self.rate_dropdown.currentText() == RATE_CPS:
            minimum = 0.1
            maximum = maximum_cps(click_type)
            corrected = min(max(value, minimum), maximum)
            if click_type == CLICK_DOUBLE:
                message = (
                    "Double-click speed is limited to 250 per second, which "
                    "sends up to 500 individual clicks."
                )
            else:
                message = "One-click speed is limited to 500 clicks per second."
        else:
            minimum = minimum_delay_ms(click_type)
            maximum = 3_600_000.0
            corrected = min(max(value, minimum), maximum)
            message = (
                f"The shortest delay for {click_type.lower()} mode is "
                f"{minimum:g} milliseconds."
            )

        if corrected == value:
            return False
        self.rate_input.setText(f"{corrected:g}")
        if notify:
            self.append_log(message)
        return True

    def repeat_changed(self, value):
        self.sync_dynamic_controls()
        self.save_preferences()

    def target_changed(self, value):
        self.sync_dynamic_controls()
        self.save_preferences()

    def hotkey_changed(self, virtual_key, modifiers, display_text):
        self.hotkey_button.set_hotkey(virtual_key, modifiers, display_text)
        self.update_hotkey_text()
        if self.hotkey_monitor is not None:
            self.hotkey_monitor.set_hotkey(virtual_key, modifiers)
        self.save_preferences()

    def hotkey_recording_changed(self, recording):
        if self.hotkey_monitor is not None:
            self.hotkey_monitor.set_enabled(not recording)
        if recording:
            self.hotkey_note.setText(
                "Press the shortcut you want • press Esc to cancel • F8 always stops"
            )
        else:
            self.update_hotkey_text()

    def update_hotkey_text(self):
        display_text = self.hotkey_button.display_text
        self.start_button.setText(
            "Stop clicking"
            if self.running
            else f"Start clicking ({display_text})"
        )
        self.hotkey_note.setText(
            f"Press {display_text} anywhere to start or stop • F8 always stops"
        )

    def topmost_changed(self, checked):
        if not self.testing:
            try:
                self.apply_native_topmost(checked)
            except OSError as error:
                signals_were_blocked = self.topmost_checkbox.blockSignals(True)
                self.topmost_checkbox.setChecked(not checked)
                self.topmost_checkbox.blockSignals(signals_were_blocked)
                self.append_log(f"Could not change the on-top setting: {error}")
        self.save_preferences()

    def apply_native_topmost(self, enabled):
        if NATIVE_USER32 is None:
            raise OSError("This setting requires Windows.")
        hwnd_value = int(self.winId())
        hwnd = wintypes.HWND(hwnd_value)
        if not hwnd_value or not NATIVE_USER32.IsWindow(hwnd):
            raise OSError("The Auto Clicker window is not available.")
        ctypes.set_last_error(0)
        insert_after = HWND_TOPMOST if enabled else HWND_NOTOPMOST
        if not NATIVE_USER32.SetWindowPos(
            hwnd,
            insert_after,
            0,
            0,
            0,
            0,
            TOPMOST_POSITION_FLAGS,
        ):
            error_code = ctypes.get_last_error()
            if error_code:
                raise ctypes.WinError(error_code)
            raise OSError("Windows could not change the on-top setting.")

    def sync_dynamic_controls(self):
        self.timing_changed_ui_only()
        repeat_mode = self.repeat_dropdown.currentText()
        repeat_enabled = repeat_mode != REPEAT_MANUAL
        self.repeat_input.setEnabled(repeat_enabled and not self.running)
        if repeat_mode == REPEAT_COUNT:
            double_click = self.type_dropdown.currentText() == CLICK_DOUBLE
            self.repeat_value_label.setText(
                "Number of double-clicks" if double_click else "Number of clicks"
            )
            self.repeat_input.setPlaceholderText("100")
            self.repeat_input.setToolTip(
                "The app stops after completing this many double-clicks."
                if double_click
                else "The app stops after completing this many clicks."
            )
        elif repeat_mode == REPEAT_SECONDS:
            self.repeat_value_label.setText("Number of seconds")
            self.repeat_input.setPlaceholderText("60")
            self.repeat_input.setToolTip(
                "The app stops after it has been clicking for this long."
            )
        else:
            self.repeat_value_label.setText("Not needed")
            self.repeat_input.setPlaceholderText("Not used")
            self.repeat_input.setToolTip(
                "Use your keyboard shortcut or F8 whenever you want to stop."
            )
        self.repeat_input.setAccessibleName(self.repeat_value_label.text())
        self.repeat_input.setAccessibleDescription(self.repeat_input.toolTip())
        fixed_enabled = self.target_dropdown.currentText() == TARGET_FIXED
        for widget in (self.x_input, self.y_input, self.capture_button):
            widget.setEnabled(fixed_enabled and not self.running)

    def timing_changed_ui_only(self):
        click_type = self.type_dropdown.currentText()
        if self.rate_dropdown.currentText() == RATE_CPS:
            self.rate_input.setPlaceholderText("10")
            if click_type == CLICK_DOUBLE:
                self.rate_value_label.setText("Double-clicks each second (max 250)")
                self.rate_input.setToolTip(
                    "Each double-click sends two clicks. At the maximum of 250 "
                    "double-clicks, that is up to 500 individual clicks each second."
                )
            else:
                self.rate_value_label.setText("Clicks each second (max 500)")
                self.rate_input.setToolTip(
                    "For example, 10 means ten clicks each second. The maximum "
                    "in one-click mode is 500."
                )
        else:
            minimum = minimum_delay_ms(click_type)
            self.rate_input.setPlaceholderText("100")
            if click_type == CLICK_DOUBLE:
                self.rate_value_label.setText("Milliseconds between double-clicks")
            else:
                self.rate_value_label.setText("Milliseconds between clicks")
            self.rate_input.setToolTip(
                f"The shortest allowed delay in this mode is {minimum:g} "
                "milliseconds. 1,000 milliseconds means one second."
            )
        self.rate_input.setAccessibleName(self.rate_value_label.text())
        self.rate_input.setAccessibleDescription(self.rate_input.toolTip())

    def current_values(self):
        return {
            "rate_mode": self.rate_dropdown.currentText(),
            "rate_value": self.rate_input.text(),
            "button": self.button_dropdown.currentText(),
            "click_type": self.type_dropdown.currentText(),
            "repeat_mode": self.repeat_dropdown.currentText(),
            "repeat_value": self.repeat_input.text(),
            "start_delay": self.delay_input.text(),
            "variation_percent": self.variation_input.text(),
            "target_mode": self.target_dropdown.currentText(),
            "target_x": self.x_input.text(),
            "target_y": self.y_input.text(),
        }

    def capture_position(self):
        try:
            x, y = self.mouse.cursor_position()
        except OSError as error:
            self.append_log(f"Could not read the cursor position: {error}")
            return
        self.x_input.setText(str(x))
        self.y_input.setText(str(y))
        self.save_preferences()
        self.append_log(f"Saved screen position set to {x}, {y}.")

    def set_controls_enabled(self, enabled):
        controls = (
            self.rate_dropdown,
            self.rate_input,
            self.button_dropdown,
            self.type_dropdown,
            self.repeat_dropdown,
            self.delay_input,
            self.variation_input,
            self.target_dropdown,
            self.hotkey_button,
        )
        for control in controls:
            control.setEnabled(enabled)
        self.topmost_checkbox.setEnabled(enabled)
        self.sync_dynamic_controls()

    def start_or_stop(self):
        if self.running:
            self.stop_clicking()
        else:
            self.start_clicking()

    def start_clicking(self):
        if self.testing or self.running:
            return
        self.enforce_rate_limit(notify=True)
        try:
            config = build_config(self.current_values())
            if config.target_mode == TARGET_FIXED and not self.mouse.virtual_screen_contains(config.target_x, config.target_y):
                raise ValueError("The fixed position is not on a connected display.")
        except ValueError as error:
            self.status_label.setText("Check the settings")
            self.append_log(str(error))
            return

        self.save_preferences()
        self.running = True
        self.active_click_type = config.click_type
        self.action_count = 0
        self.update_count(0)
        stop_event = threading.Event()
        self.worker_stop = stop_event
        if self.hotkey_monitor is not None:
            self.hotkey_monitor.set_active_stop_event(stop_event)
        self.set_controls_enabled(False)
        self.start_button.setText("Stop clicking")
        self.start_button.setObjectName("danger")
        self.start_button.style().unpolish(self.start_button)
        self.start_button.style().polish(self.start_button)
        target = (
            "wherever the mouse cursor is"
            if config.target_mode == TARGET_CURSOR
            else f"the saved spot at {config.target_x}, {config.target_y}"
        )
        if config.rate_mode == RATE_CPS:
            speed_text = (
                f"{config.rate_value:g} double-clicks each second"
                if config.double_click
                else f"{config.rate_value:g} clicks each second"
            )
        else:
            speed_text = (
                f"{config.rate_value:g} milliseconds between double-clicks"
                if config.double_click
                else f"{config.rate_value:g} milliseconds between clicks"
            )
        self.append_log(
            f"Started: {config.button.lower()} button, {config.click_type.lower()}, "
            f"{speed_text}, "
            f"clicking {target}."
        )

        def worker():
            try:
                state, actions, message = run_click_job(
                    config,
                    stop_event,
                    self.mouse,
                    self.bridge.count_changed.emit,
                    self.bridge.status_changed.emit,
                )
            except BaseException as error:
                state = "failed"
                actions = 0
                message = f"The click worker stopped unexpectedly: {error}"
            self.bridge.job_finished.emit(state, actions, message)

        try:
            worker_thread = threading.Thread(
                target=worker,
                name="FleeceClickWorker",
                daemon=True,
            )
            self.worker_thread = worker_thread
            worker_thread.start()
        except Exception as error:
            stop_event.set()
            if self.hotkey_monitor is not None:
                self.hotkey_monitor.set_active_stop_event(None)
            self.running = False
            self.worker_thread = None
            self.worker_stop = None
            self.start_button.setObjectName("primary")
            self.start_button.setText(
                f"Start clicking ({self.hotkey_button.display_text})"
            )
            self.start_button.style().unpolish(self.start_button)
            self.start_button.style().polish(self.start_button)
            self.set_controls_enabled(True)
            self.status_label.setText("Could not start clicking")
            self.append_log(f"The click worker could not start: {error}")

    def stop_clicking(self):
        if not self.running or self.worker_stop is None:
            return
        self.status_label.setText("Stopping…")
        self.worker_stop.set()

    def job_finished(self, state, actions, message):
        self.running = False
        if self.hotkey_monitor is not None:
            self.hotkey_monitor.set_active_stop_event(None)
        self.action_count = actions
        self.update_count(actions)
        self.start_button.setObjectName("primary")
        self.start_button.setText(
            f"Start clicking ({self.hotkey_button.display_text})"
        )
        self.start_button.style().unpolish(self.start_button)
        self.start_button.style().polish(self.start_button)
        self.set_controls_enabled(True)
        if state == "completed":
            self.status_label.setText("Completed")
        elif state == "failed":
            self.status_label.setText("Clicking failed")
        else:
            self.status_label.setText("Ready")
        action_name = (
            "double-click" if self.active_click_type == CLICK_DOUBLE else "click"
        )
        self.append_log(
            f"{message} {actions:,} {action_name}"
            f"{'s' if actions != 1 else ''} completed."
        )
        self.worker_thread = None
        self.worker_stop = None

    def status_label_text(self, text):
        self.status_label.setText(text)

    def update_count(self, count):
        self.action_count = count
        self.count_label.setText(f"{count:,} completed")

    def append_log(self, message):
        self.log_box.append(f"[{time.strftime('%H:%M:%S')}] {message}")
        self.log_box.moveCursor(QTextCursor.End)

    def clear_log(self):
        self.log_box.clear()

    def open_safety(self):
        if self.safety_window is None:
            self.safety_window = SafetyWindow(self)
        self.safety_window.move(self.frameGeometry().center() - self.safety_window.rect().center())
        self.safety_window.show()
        self.safety_window.raise_()
        self.safety_window.activateWindow()

    def closeEvent(self, event: QCloseEvent):
        if self.running and not native_question(
            "Auto Clicker is active. Stop clicking and close?",
            owner=self.winId(),
        ):
            event.ignore()
            return
        if self.worker_stop is not None:
            self.worker_stop.set()
        if self.hotkey_monitor is not None:
            self.hotkey_monitor.close()
            self.hotkey_monitor.join(timeout=1.0)
        if self.worker_thread is not None:
            self.worker_thread.join(timeout=1.5)
        self.save_preferences()
        self._settings_sync_timer.stop()
        self.settings.sync()
        event.accept()


class FakeMouse:
    def __init__(self):
        self.clicks = []
        self.moves = []

    def click(self, button, double_click=False):
        self.clicks.append((button, double_click))

    def move_to(self, x, y):
        self.moves.append((x, y))

    @staticmethod
    def virtual_screen_contains(x, y):
        return True


def run_self_test(output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    checks = []

    values = {
        "rate_mode": RATE_CPS,
        "rate_value": "20",
        "button": "Left",
        "click_type": CLICK_ONCE,
        "repeat_mode": REPEAT_COUNT,
        "repeat_value": "5",
        "start_delay": "0",
        "variation_percent": "0",
        "target_mode": TARGET_FIXED,
        "target_x": "120",
        "target_y": "240",
    }
    config = build_config(values)
    assert abs(config.interval_seconds - 0.05) < 0.000001
    checks.append("CPS timing and validation")

    interval_values = dict(values, rate_mode=RATE_DELAY, rate_value="250")
    assert abs(build_config(interval_values).interval_seconds - 0.25) < 0.000001
    checks.append("millisecond timing")

    invalid_values = dict(values, rate_value="0")
    try:
        build_config(invalid_values)
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid click rate was accepted.")
    checks.append("invalid input rejection")

    assert build_config(dict(values, rate_value="500")).rate_value == 500
    assert build_config(
        dict(values, click_type=CLICK_DOUBLE, rate_value="250")
    ).rate_value == 250
    for limited_values in (
        dict(values, rate_value="500.1"),
        dict(values, click_type=CLICK_DOUBLE, rate_value="250.1"),
        dict(values, rate_mode=RATE_DELAY, rate_value="1.9"),
        dict(
            values,
            click_type=CLICK_DOUBLE,
            rate_mode=RATE_DELAY,
            rate_value="3.9",
        ),
    ):
        try:
            build_config(limited_values)
        except ValueError:
            pass
        else:
            raise AssertionError("A mode-specific speed limit was bypassed.")
    assert build_config(
        dict(values, rate_mode=RATE_DELAY, rate_value="2")
    ).interval_seconds == 0.002
    assert build_config(
        dict(
            values,
            click_type=CLICK_DOUBLE,
            rate_mode=RATE_DELAY,
            rate_value="4",
        )
    ).interval_seconds == 0.004
    checks.append("one-click and double-click hard speed limits")

    class FastestVariation:
        @staticmethod
        def uniform(lower, upper):
            return lower

    fastest_variation = FastestVariation()
    varied_single = build_config(
        dict(values, rate_value="500", variation_percent="50")
    )
    varied_double = build_config(
        dict(
            values,
            click_type=CLICK_DOUBLE,
            rate_value="250",
            variation_percent="50",
        )
    )
    varied_delay_single = build_config(
        dict(
            values,
            rate_mode=RATE_DELAY,
            rate_value="2",
            variation_percent="50",
        )
    )
    varied_delay_double = build_config(
        dict(
            values,
            click_type=CLICK_DOUBLE,
            rate_mode=RATE_DELAY,
            rate_value="4",
            variation_percent="50",
        )
    )
    assert scheduled_interval_seconds(varied_single, fastest_variation) == 0.002
    assert scheduled_interval_seconds(varied_double, fastest_variation) == 0.004
    assert (
        scheduled_interval_seconds(varied_delay_single, fastest_variation)
        == 0.002
    )
    assert (
        scheduled_interval_seconds(varied_delay_double, fastest_variation)
        == 0.004
    )
    checks.append("random timing cannot bypass hard speed limits")

    class OversleepClock:
        def __init__(self):
            self.value = 0.0
            self.waits = 0

        def now(self):
            return self.value

        def wait(self, deadline, stop_event):
            oversleep = 0.010 if self.waits == 0 else 0.0
            self.waits += 1
            self.value = deadline + oversleep
            return stop_event.is_set()

    class ClockedMouse:
        def __init__(self, clock):
            self.clock = clock
            self.click_times = []
            self.send_durations = iter(
                (0.0007, 0.0011, 0.0002, 0.0030, 0.0004, 0.0015, 0.0001, 0.0008)
            )

        def click(self, button, double_click=False):
            self.click_times.append(self.clock.now())
            self.clock.value += next(self.send_durations)

        def move_to(self, x, y):
            pass

    for limited_values, minimum_gap in (
        (dict(values, rate_value="500", repeat_value="8", target_mode=TARGET_CURSOR), 0.002),
        (
            dict(
                values,
                click_type=CLICK_DOUBLE,
                rate_value="250",
                repeat_value="8",
                target_mode=TARGET_CURSOR,
            ),
            0.004,
        ),
    ):
        fake_clock = OversleepClock()
        clocked_mouse = ClockedMouse(fake_clock)
        state, actions, _ = run_click_loop(
            build_config(limited_values),
            threading.Event(),
            clocked_mouse,
            lambda count: None,
            lambda text: None,
            random.Random(1),
            fake_clock.wait,
            fake_clock.now,
        )
        gaps = [
            later - earlier
            for earlier, later in zip(
                clocked_mouse.click_times,
                clocked_mouse.click_times[1:],
            )
        ]
        assert state == "completed" and actions == 8
        assert gaps and min(gaps) >= minimum_gap - 0.000000001
    checks.append("scheduler never bursts to catch up after an oversleep")

    fake = FakeMouse()
    state, actions, _ = run_click_job(config, threading.Event(), fake)
    assert state == "completed" and actions == 5
    assert fake.clicks == [("Left", False)] * 5
    assert fake.moves == [(120, 240)] * 5
    checks.append("bounded fixed-position click plan (no real input sent)")

    double_values = dict(
        values,
        click_type=CLICK_DOUBLE,
        repeat_value="3",
        target_mode=TARGET_CURSOR,
    )
    double_fake = FakeMouse()
    state, actions, _ = run_click_job(build_config(double_values), threading.Event(), double_fake)
    assert state == "completed" and actions == 3
    assert double_fake.clicks == [("Left", True)] * 3 and not double_fake.moves
    checks.append("double-click plan (no real input sent)")

    speed_values = dict(
        values,
        rate_value="200",
        repeat_value="40",
        target_mode=TARGET_CURSOR,
    )
    speed_fake = FakeMouse()
    speed_started = time.perf_counter()
    state, actions, _ = run_click_job(
        build_config(speed_values), threading.Event(), speed_fake
    )
    speed_elapsed = time.perf_counter() - speed_started
    assert state == "completed" and actions == 40
    assert 0.15 <= speed_elapsed < 0.50
    checks.append("high-resolution 200-clicks-per-second scheduler")

    cancelled = threading.Event()
    cancelled.set()
    state, actions, _ = run_click_job(config, cancelled, FakeMouse())
    assert state == "stopped" and actions == 0
    checks.append("emergency cancellation path")

    wide_count = 5_000_000_000
    received_counts = []
    received_finishes = []
    wide_bridge = UiBridge()
    wide_bridge.count_changed.connect(received_counts.append)
    wide_bridge.job_finished.connect(
        lambda state, count, message: received_finishes.append(
            (state, count, message)
        )
    )
    wide_bridge.count_changed.emit(wide_count)
    wide_bridge.job_finished.emit("completed", wide_count, "done")
    assert received_counts == [wide_count]
    assert received_finishes == [("completed", wide_count, "done")]
    checks.append("64-bit action count signals")

    expected_input_size = 40 if ctypes.sizeof(ctypes.c_void_p) == 8 else 28
    assert ctypes.sizeof(Input) == expected_input_size
    checks.append("architecture-safe Windows input structure")

    click_packet = (Input * 4)()
    release_packet = (Input * 1)()
    send_counts = []
    send_results = iter((1, 1))

    def partial_sender(count, packet, structure_size):
        send_counts.append(count)
        return next(send_results)

    ctypes.set_last_error(0)
    safe_sender = _build_click_sender(
        partial_sender,
        click_packet,
        release_packet,
        ctypes.sizeof(Input),
    )
    try:
        safe_sender()
    except OSError:
        pass
    else:
        raise AssertionError("Partial mouse input insertion was accepted.")
    assert send_counts == [4, 1]

    blocked_sender = _build_click_sender(
        lambda count, packet, structure_size: 0,
        click_packet,
        release_packet,
        ctypes.sizeof(Input),
    )
    try:
        blocked_sender()
    except OSError as error:
        assert "administrator" in str(error)
    else:
        raise AssertionError("Blocked mouse input did not report a failure.")
    checks.append("partial or blocked mouse input fails safely")

    assert APP_MUTEX_NAMES == (
        r"Global\FleeceAutoClickerApp",
        r"Local\FleeceAutoClickerApp",
    )
    assert APP_MUTEX_NAME in APP_MUTEX_NAMES
    assert SETUP_LOCK_DIR == RUNTIME_DIR / "setup.lock"
    checks.append("Auto Clicker-specific app and setup locks")

    if NATIVE_KERNEL32 is not None:
        test_mutex_name = (
            rf"Local\FleeceAutoClickerSelfTest-{os.getpid()}-{time.time_ns()}"
        )
        first_status, first_handle = _try_create_named_mutex(test_mutex_name)
        try:
            second_status, second_handle = _try_create_named_mutex(test_mutex_name)
            assert first_status == "acquired" and first_handle
            assert second_status == "exists" and second_handle is None
        finally:
            if first_handle:
                NATIVE_KERNEL32.CloseHandle(first_handle)
    checks.append("a second app-instance mutex is rejected")

    pressed = {0x11, ord("K")}
    key_down = lambda key: key in pressed
    assert hotkey_state_matches(ord("K"), HOTKEY_CTRL, key_down)
    assert not hotkey_state_matches(ord("K"), HOTKEY_CTRL | HOTKEY_SHIFT, key_down)
    pressed.add(0x12)
    assert not hotkey_state_matches(ord("K"), HOTKEY_CTRL, key_down)
    checks.append("custom keyboard shortcut matching")

    for rejected_key in (
        0,
        0x01,
        0x02,
        EMERGENCY_VK,
        0x10,
        0x11,
        0x12,
        0x5B,
        0x5C,
        0xFF,
        0x100,
    ):
        assert normalize_hotkey(rejected_key, 0xFFFF) == (
            DEFAULT_HOTKEY_VK,
            0,
        )
    assert normalize_hotkey(ord("K"), 0x101) == (ord("K"), HOTKEY_CTRL)
    assert hotkey_display_text(0x61, HOTKEY_CTRL) == "Ctrl+Numpad 1"
    checks.append("unsafe shortcuts rejected and modifier bits masked")

    emergency_event = threading.Event()
    hotkey_probe = HotkeyMonitor(
        UiBridge(),
        DEFAULT_HOTKEY_VK,
        0,
        key_state_reader=lambda key: 0x8000 if key == EMERGENCY_VK else 0,
    )
    hotkey_probe.set_active_stop_event(emergency_event)
    hotkey_probe.start()
    assert emergency_event.wait(0.25)
    hotkey_probe.close()
    hotkey_probe.join(timeout=0.5)
    assert not hotkey_probe.is_alive()
    checks.append("F8 directly stops an active worker without Qt event delivery")

    capture = HotkeyCaptureButton()
    captured = []
    capture.changed.connect(
        lambda key, modifiers, text: captured.append((key, modifiers, text))
    )
    capture.begin_recording()
    capture.keyPressEvent(
        QKeyEvent(
            QEvent.KeyPress,
            Qt.Key_K,
            Qt.ControlModifier | Qt.ShiftModifier,
            0,
            ord("K"),
            0,
            "K",
        )
    )
    assert captured == [(ord("K"), HOTKEY_CTRL | HOTKEY_SHIFT, "Ctrl+Shift+K")]
    capture.begin_recording()
    capture.keyPressEvent(
        QKeyEvent(
            QEvent.KeyPress,
            Qt.Key_1,
            Qt.KeypadModifier,
            0,
            0x61,
            0,
            "1",
        )
    )
    assert captured[-1] == (0x61, 0, "Numpad 1")
    capture.begin_recording()
    capture.keyPressEvent(
        QKeyEvent(
            QEvent.KeyPress,
            Qt.Key_F8,
            Qt.NoModifier,
            0,
            EMERGENCY_VK,
            0,
        )
    )
    assert capture.recording and len(captured) == 2
    capture.cancel_recording()

    class FallbackFunctionKeyEvent:
        @staticmethod
        def nativeVirtualKey():
            return 0

        @staticmethod
        def key():
            return int(Qt.Key_F12)

    assert qt_key_to_virtual_key(FallbackFunctionKeyEvent()) == 0x7B
    checks.append("keyboard shortcut capture control")

    settings_path = output_dir / "settings-test.ini"
    settings = QSettings(str(settings_path), QSettings.IniFormat)
    settings.setValue("hotkey_display", "Ctrl+K")
    settings.setValue("hotkey_vk", ord("K"))
    settings.setValue("hotkey_modifiers", HOTKEY_CTRL)
    settings.setValue("topmost", False)
    settings.sync()
    check_settings = QSettings(str(settings_path), QSettings.IniFormat)
    assert check_settings.value("hotkey_display") == "Ctrl+K"
    assert int(check_settings.value("hotkey_vk")) == ord("K")
    assert int(check_settings.value("hotkey_modifiers")) == HOTKEY_CTRL
    assert str(check_settings.value("topmost")).lower() == "false"
    checks.append("local settings round-trip")

    corrupt_settings_path = output_dir / "corrupt-settings-test.ini"
    corrupt_settings = QSettings(
        str(corrupt_settings_path),
        QSettings.IniFormat,
    )
    corrupt_settings.setValue("hotkey_vk", 0x01)
    corrupt_settings.setValue("hotkey_modifiers", 0xFFFF)
    corrupt_settings.setValue("hotkey_display", "unsafe\nmouse shortcut")
    corrupt_settings.sync()
    corrupt_window = AutoClicker(
        testing=True,
        settings_path=corrupt_settings_path,
    )
    assert corrupt_window.hotkey_button.virtual_key == DEFAULT_HOTKEY_VK
    assert corrupt_window.hotkey_button.modifiers == 0
    assert corrupt_window.hotkey_button.display_text == "F6"
    corrupt_window.close()

    numpad_settings_path = output_dir / "numpad-settings-test.ini"
    numpad_settings = QSettings(str(numpad_settings_path), QSettings.IniFormat)
    numpad_settings.setValue("hotkey_vk", 0x61)
    numpad_settings.setValue("hotkey_modifiers", HOTKEY_CTRL | 0x100)
    numpad_settings.setValue("hotkey_display", "not the canonical name")
    numpad_settings.sync()
    numpad_window = AutoClicker(
        testing=True,
        settings_path=numpad_settings_path,
    )
    assert numpad_window.hotkey_button.virtual_key == 0x61
    assert numpad_window.hotkey_button.modifiers == HOTKEY_CTRL
    assert numpad_window.hotkey_button.display_text == "Ctrl+Numpad 1"
    numpad_window.close()
    checks.append("corrupt shortcut settings recover to canonical safe values")

    dropdown_host = QWidget()
    dropdown_layout = QVBoxLayout(dropdown_host)
    dropdown = AnimatedDropdown(["First", "Second", "Third"])
    dropdown_layout.addWidget(dropdown)
    dropdown_host.resize(280, 220)
    dropdown_host.move(40, 40)
    dropdown_host.show()
    QApplication.processEvents()
    dropdown.button.setFocus()
    QApplication.sendEvent(
        dropdown.button,
        QKeyEvent(QEvent.KeyPress, Qt.Key_Down, Qt.NoModifier),
    )
    QApplication.processEvents()
    assert dropdown.popup.isVisible()
    assert QApplication.focusWidget() is dropdown.option_buttons[0]
    QApplication.sendEvent(
        dropdown.option_buttons[0],
        QKeyEvent(QEvent.KeyPress, Qt.Key_End, Qt.NoModifier),
    )
    assert QApplication.focusWidget() is dropdown.option_buttons[-1]
    QApplication.sendEvent(
        dropdown.option_buttons[-1],
        QKeyEvent(QEvent.KeyPress, Qt.Key_Return, Qt.NoModifier),
    )
    assert dropdown.currentText() == "Third"
    assert dropdown.option_buttons[-1].isChecked()
    dropdown.hide_popup(restore_focus=True, immediate=True)
    QApplication.processEvents()
    assert QApplication.focusWidget() is dropdown.button

    dropdown.show_popup(focus_index=2)
    QApplication.processEvents()
    popup_before_move = dropdown.popup.geometry()
    dropdown_host.move(90, 70)
    QApplication.processEvents()
    assert dropdown.popup.geometry().topLeft() != popup_before_move.topLeft()
    dropdown_host.resize(320, 240)
    QApplication.processEvents()
    assert dropdown.popup.width() == dropdown.width()
    screen = QApplication.screenAt(dropdown.button.mapToGlobal(QPoint(0, 0)))
    if screen is None:
        screen = QApplication.primaryScreen()
    if screen is not None:
        available = screen.availableGeometry()
        assert available.contains(dropdown.popup.frameGeometry())
        dropdown_host.move(available.right() - 40, available.bottom() - 40)
        QApplication.processEvents()
        QApplication.processEvents()
        assert available.contains(dropdown.popup.frameGeometry()), (
            available,
            dropdown.popup.geometry(),
            dropdown.popup.frameGeometry(),
            dropdown._popup_geometry(),
        )
    QApplication.sendEvent(
        dropdown.option_buttons[-1],
        QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier),
    )
    assert dropdown._closing
    dropdown.hide_popup(immediate=True)

    dropdown.show_popup()
    QApplication.processEvents()
    QApplication.sendEvent(
        QApplication.instance(),
        QEvent(QEvent.ApplicationDeactivate),
    )
    assert not dropdown.popup.isVisible()
    dropdown.show_popup()
    QApplication.processEvents()
    dropdown.setEnabled(False)
    assert not dropdown.popup.isVisible()
    dropdown.setEnabled(True)
    dropdown_host.close()
    checks.append("dropdown keyboard, focus, clamping, and host lifecycle")

    responsive_settings_path = output_dir / "responsive-settings-test.ini"
    responsive_window = AutoClicker(
        testing=True,
        settings_path=responsive_settings_path,
    )
    responsive_window.show()
    QApplication.processEvents()
    assert responsive_window.size().width() == 680
    assert responsive_window.size().height() == 748
    assert responsive_window.content_scroll.verticalScrollBar().maximum() == 0
    assert responsive_window.rate_value_label.buddy() is responsive_window.rate_input
    assert responsive_window.repeat_value_label.buddy() is responsive_window.repeat_input
    assert responsive_window.delay_label.buddy() is responsive_window.delay_input
    assert responsive_window.variation_label.buddy() is responsive_window.variation_input
    assert all(
        line_edit.accessibleName()
        for line_edit in (
            responsive_window.rate_input,
            responsive_window.repeat_input,
            responsive_window.delay_input,
            responsive_window.variation_input,
            responsive_window.x_input,
            responsive_window.y_input,
        )
    )
    assert all(
        button.accessibleName()
        for button in responsive_window.findChildren(TrafficLightButton)
    )
    responsive_window.resize(500, 500)
    QApplication.processEvents()
    assert responsive_window.content_scroll.verticalScrollBar().maximum() > 0
    assert responsive_window.content_scroll.horizontalScrollBar().maximum() > 0
    responsive_window.close()
    checks.append("small screens scroll while the 680 by 748 layout is unchanged")

    startup_settings_path = output_dir / "startup-rollback-settings-test.ini"
    startup_window = AutoClicker(
        testing=True,
        settings_path=startup_settings_path,
    )
    startup_window.testing = False
    startup_window.mouse = FakeMouse()
    original_thread_start = threading.Thread.start

    def fail_thread_start(thread):
        raise RuntimeError("deterministic self-test failure")

    threading.Thread.start = fail_thread_start
    try:
        startup_window.start_clicking()
    finally:
        threading.Thread.start = original_thread_start
    assert not startup_window.running
    assert startup_window.worker_thread is None
    assert startup_window.worker_stop is None
    assert startup_window.start_button.objectName() == "primary"
    assert startup_window.start_button.isEnabled()
    assert startup_window.rate_dropdown.isEnabled()
    assert startup_window.status_label.text() == "Could not start clicking"
    startup_window.testing = True
    startup_window.close()
    checks.append("worker thread start failure fully rolls back the UI")

    marker = output_dir / "self-test-passed.txt"
    marker.write_text("\n".join(checks) + "\n", encoding="utf-8")
    print(f"Auto Clicker self-test passed ({len(checks)} checks).")
    return 0


def screenshot_app(output_path):
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    window = AutoClicker(testing=True, settings_path=RUNTIME_DIR / "screenshot-settings.ini")
    window.show()
    QApplication.processEvents()
    image = window.grab()
    if not image.save(str(output_path), "PNG"):
        raise OSError(f"Could not save screenshot to {output_path}")
    window.close()
    print(f"Saved {output_path}")
    return 0


def main():
    if os.name != "nt":
        show_native_error("Auto Clicker supports 64-bit Windows only.")
        return 1
    if "--self-test" in sys.argv:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    elif "--screenshot" in sys.argv:
        os.environ.setdefault("QT_QPA_PLATFORM", "windows")
    else:
        if not acquire_app_mutex():
            show_native_error("Auto Clicker is already open.")
            return 1
        if SETUP_LOCK_DIR.is_dir():
            show_native_error(
                "Auto Clicker setup is currently running.\n\n"
                "Let Installer.bat finish, then open the app again."
            )
            return 1
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("fleece.auto-clicker")
    except (AttributeError, OSError):
        pass
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("Fleece")
    sys.excepthook = handle_unhandled_exception

    if "--self-test" in sys.argv:
        index = sys.argv.index("--self-test")
        output = sys.argv[index + 1] if index + 1 < len(sys.argv) else RUNTIME_DIR / "self-test"
        try:
            return run_self_test(output)
        except Exception:
            traceback.print_exc()
            return 1
    if "--screenshot" in sys.argv:
        index = sys.argv.index("--screenshot")
        if index + 1 >= len(sys.argv):
            print("--screenshot requires an output path", file=sys.stderr)
            return 2
        try:
            return screenshot_app(sys.argv[index + 1])
        except Exception:
            traceback.print_exc()
            return 1

    window = AutoClicker()
    screen = QApplication.primaryScreen()
    if screen is not None:
        available = screen.availableGeometry()
        window.resize(
            min(window.width(), available.width()),
            min(window.height(), available.height()),
        )
        window.move(screen.availableGeometry().center() - window.rect().center())
    window.show()
    if window.topmost_checkbox.isChecked():
        window.topmost_changed(True)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
