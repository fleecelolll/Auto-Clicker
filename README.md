<div align="center">

# auto clicker

Current audit update: **v1.0.12**. Includes app-specific bug fixes, bounded offline regression/performance tests, and shared setup hardening.

All Fleece desktop tools use the same installation workflow: download the official ZIP, extract the entire folder, run `Installer.bat`, accept the bundled Terms/Tool License, wait for final checks, then open the folder-local shortcut. Setup installs a private runtime without changing system Python or requiring administrator access. Rerun it to repair or refresh a moved shortcut. Keep the full path at most 72 characters, without percent signs. Architecture support and extra components vary by tool; File Converter remains x64-only.

A little tool I made with AI to automate mouse clicking locally on 64-bit Windows.

<img src="Auto%20Clicker.png" alt="Auto Clicker app window" width="760">

</div>

## features

- Use left, right, or middle mouse clicks
- Choose single-click or double-click actions
- Set exact clicks per second or millisecond timing
- Run until stopped, for a click count, or for a duration
- Add a start delay and randomized timing variation
- Click at the cursor or a saved screen position
- Choose a global start-and-stop keyboard shortcut
- Keep F8 available as a fixed emergency stop

## requirements

- 64-bit x64 or ARM64 Windows
- An internet connection during first setup
- Permission to automate the target app or website
- No internet connection while using the installed app

## installation

1. Download the latest release ZIP.
2. Extract the complete folder.
3. Double-click `Installer.bat`.
4. Press **Y** once to accept the Terms and bundled Tool License and approve setup.
5. Leave the setup window open until every check passes.
6. Double-click the `Auto Clicker` shortcut created in the folder.

Keep the full extracted folder path at 72 characters or fewer so Windows can install the private packages reliably.

Setup keeps the private Python runtime, dependencies, settings, and every app component inside the extracted folder. It does not require administrator access, change PATH, or install global Python packages. The generated folder-local shortcut starts the app directly with that private runtime, so Microsoft Store or system Python is not required.

Setup pins and verifies official Python 3.14.7, pip, and PySide6-Essentials. Downloaded runtime archives and the complete PyPI wheel dependency set are checked against pinned SHA-256 hashes before use. Setup automatically selects the bundled x64 or ARM64 requirements file; keep both files with the extracted release.

Run `Installer.bat` again to repair the private components or after moving the complete folder. Setup preserves saved clicking preferences and recreates the shortcut for the folder's current location.

## 1.0.11 security update

- Require reviewed SHA-256 hashes for every Python dependency download during setup and repair.
- Include complete architecture-specific dependency lock files in the release ZIP.
- Keep the same UI, dependency versions, public download, and folder-local setup process.

## usage

1. Choose the click speed, button, action, stop condition, and position.
2. Click the shortcut box and press a key combination to change it.
3. Press **Start clicking** or the saved keyboard shortcut.
4. Press the same shortcut to stop, or press **F8** for the emergency stop.

One-click mode supports up to 500 clicks per second. Double-click mode supports up to 250 double-click actions per second. The rate another app receives still depends on Windows, that app, and the computer.

These are maximum allowed rates, not a guarantee of delivery speed. Test a low rate first, especially at a saved position. Random timing never exceeds these caps. Count mode allows up to 1,000,000,000 actions; duration mode allows up to 7 days, and the start delay allows up to 1 hour. The activity view retains the latest 500 lines.

## built with

- [PySide6](https://doc.qt.io/qtforpython-6/)
- Windows `SendInput`
- [Python](https://www.python.org/)

## privacy and removal

The app has no telemetry, analytics, advertisements, accounts, or runtime network requests. Preferences stay in `.runtime\settings.ini` inside the extracted folder. Setup logs can contain local folder paths, so review them before sharing.

To remove Auto Clicker, close it and delete the extracted folder. This removes its folder-local shortcut, private runtime, dependencies, settings, and app files. The app does not install a background service, add itself to startup, or create an uninstaller entry.

## troubleshooting

If setup stops, the window shows the failed check and a short **How to fix it** instruction; the same guidance is saved in `setup.log`. Setup checks the bundled app source and Windows shortcut support before downloading large components, then compiles source before downloading app packages. Correct the problem and run `Installer.bat` again. Success is reported only after dependencies, offline self-tests, and the shortcut all pass.

If the `Auto Clicker` shortcut does not open, run `Installer.bat` again and keep the complete extracted folder together. Setup recreates and validates the shortcut for the folder's current location.

If a keyboard shortcut is already reserved by Windows or another app, choose a different combination. F8 is the fixed emergency stop while the keyboard monitor is working. If that monitor fails, the app stops the active click job and blocks new jobs; restart the app to restore the shortcuts.

## offline regression checks

From the extracted source folder, run `.runtime\python\python.exe -I scripts\Test-AppSafety.py`. The suite uses fake mouse input, an offscreen Qt window, and disposable preference files. It never clicks the desktop. It checks malformed input, cancellation and duration boundaries, emergency-stop failures, settings, log limits, and bounded scheduler/GUI-response workloads. Use `--report PATH` to save measurements as JSON. Timing budgets are regression tripwires, not performance guarantees for another app or computer.

## license

Copyright 2026 Fleece. This project is source-available, not open source. The bundled [LICENSE](LICENSE) permits downloading, installing, and running an unmodified official release for lawful personal, non-commercial use. Modification, redistribution, sale, rebranding, and derivative versions remain prohibited. Third-party materials retain their own licenses.

## note

This project was made with AI.

Only automate clicking where you have permission. Keep F8 available, especially when using high rates or a fixed position.
