<div align="center">

# auto clicker

A little tool I made with AI to automate mouse clicking locally on 64-bit Windows.

<img src="Auto%20Clicker.png" alt="Auto Clicker app window" width="680">

</div>

## features

- Left, right, and middle mouse buttons
- Single-click and double-click actions
- High-precision clicks-per-second or exact millisecond timing
- Up to 500 single clicks per second or 250 double-click actions per second
- Run until stopped, for a click count, or for a duration
- Optional start delay and randomized timing variation
- Click wherever the cursor is or keep clicking a fixed screen position
- Fully customizable global keyboard shortcut for starting and stopping
- Fixed global F8 emergency stop
- Optional always-on-top window
- Remembers your settings locally

## installation

1. Download and extract the release ZIP.
2. Double-click `Installer.bat`.
3. Let every setup check pass.
4. Double-click the `Auto Clicker` shortcut created in the folder.

The setup installs and verifies official 64-bit Python 3.14.7 privately in `.runtime\python` inside the extracted folder. The app shortcut uses that private runtime directly, so it does not depend on Microsoft Store or system Python. Setup does not need administrator access, change PATH, or install global packages. It also installs one small shared launcher in `%LOCALAPPDATA%\Fleece Tools\Python Launcher` and sets `.pyw` files to open with it for your Windows account. The launcher prefers the selected tool's sibling `.runtime\python\pythonw.exe` and keeps a legacy `.venv\Scripts\pythonw.exe` fallback for older Fleece Tool releases; it never uses another tool's Python. You can copy the shortcut to your Desktop or pin it to the taskbar.

Before the first Fleece Tools association change, setup exports any existing per-user `.pyw` settings to that shared folder. If the previous setting cannot be backed up safely, setup stops without overwriting it. A later non-Fleece choice is also left alone.

## usage

1. Choose how fast to click, what the click should do, when it should stop, and where it should click.
2. To change the keyboard shortcut, click its box and press the key combination you want.
3. Press **Start clicking** or your saved keyboard shortcut.
4. Press the same shortcut to stop, or press **F8** at any time for the emergency stop.

When **Always click one saved spot** is selected, use **Use cursor position** to save the pointer's current location. The pointer will move back there before every click.

One-click mode allows up to 500 clicks per second, with a shortest delay of 2 milliseconds. Double-click mode allows up to 250 double-clicks per second, with a shortest delay of 4 milliseconds; because each double-click sends two clicks, that is up to 500 individual clicks per second. The exact rate another app or website can receive still depends on that app, Windows, and the computer.

## built with

- Python
- PySide6 / Qt
- Windows `SendInput`
- AI-assisted development

## privacy and removal

The app runs locally. It has no accounts, analytics, telemetry, advertisements, or runtime network requests. Preferences are stored only in `.runtime/settings.ini` inside the app folder.

To remove only Auto Clicker, delete the extracted folder. The app does not install a background service, add itself to startup, or create an uninstaller entry.

The shared `.pyw` launcher is used by every installed Fleece Tool, so removing one tool does not remove it. To restore the `.pyw` settings that existed before Fleece Tools first configured them, run `%LOCALAPPDATA%\Fleece Tools\Python Launcher\Restore pyw association.cmd`. The restore helper refuses to overwrite a newer non-Fleece choice. After restoring, and after removing every Fleece Tool that uses it, you can delete the shared `Python Launcher` folder. The registry backup files can contain local application names and paths, so review them before sharing.

## source use

The source is public for transparency and security review. Copyright 2026 Fleece. All rights reserved. No license is granted to use, modify, redistribute, sell, or publish derivative versions beyond the limited rights provided by the hosting platform.

## note

This project was made with AI.

Only automate clicking where you have permission. Keep F8 available as the emergency stop, especially with high rates or fixed-position clicking.
