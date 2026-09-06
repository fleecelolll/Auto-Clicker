<div align="center">

# auto clicker

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
4. Press **Y** once to approve setup.
5. Leave the setup window open until every check passes.
6. Double-click the `Auto Clicker` shortcut created in the folder.

Keep the full extracted folder path at 72 characters or fewer so Windows can install the private packages reliably.

Setup keeps the private Python runtime, dependencies, settings, and every app component inside the extracted folder. It does not require administrator access, change PATH, or install global Python packages. The generated folder-local shortcut starts the app directly with that private runtime, so Microsoft Store or system Python is not required.

Setup pins and verifies official Python 3.14.7, pip, and PySide6-Essentials. Downloaded runtime archives are checked against pinned SHA-256 hashes before use.

Run `Installer.bat` again to repair the private components or after moving the complete folder. Setup preserves saved clicking preferences and recreates the shortcut for the folder's current location.

## usage

1. Choose the click speed, button, action, stop condition, and position.
2. Click the shortcut box and press a key combination to change it.
3. Press **Start clicking** or the saved keyboard shortcut.
4. Press the same shortcut to stop, or press **F8** for the emergency stop.

One-click mode supports up to 500 clicks per second. Double-click mode supports up to 250 double-click actions per second. The rate another app receives still depends on Windows, that app, and the computer.

## built with

- [PySide6](https://doc.qt.io/qtforpython-6/)
- Windows `SendInput`
- [Python](https://www.python.org/)

## privacy and removal

The app has no telemetry, analytics, advertisements, accounts, or runtime network requests. Preferences stay in `.runtime\settings.ini` inside the extracted folder. Setup logs can contain local folder paths, so review them before sharing.

To remove Auto Clicker, close it and delete the extracted folder. This removes its folder-local shortcut, private runtime, dependencies, settings, and app files. The app does not install a background service, add itself to startup, or create an uninstaller entry.

## troubleshooting

If setup stops, review `setup.log`, correct the listed problem, and run `Installer.bat` again. Setup reports success only after its dependencies, offline self-tests, and shortcut all pass.

If the `Auto Clicker` shortcut does not open, run `Installer.bat` again and keep the complete extracted folder together. Setup recreates and validates the shortcut for the folder's current location.

If a keyboard shortcut is already reserved by Windows or another app, choose a different combination. F8 always remains the emergency stop.

## source use

The source is public for transparency and security review. Copyright 2026 Fleece. All rights reserved. No permission is granted to use, copy, modify, redistribute, sell, or publish derivative versions. See [LICENSE](LICENSE).

## note

This project was made with AI.

Only automate clicking where you have permission. Keep F8 available, especially when using high rates or a fixed position.
