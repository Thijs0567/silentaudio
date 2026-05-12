# silentaudio

> **Device-specific:** This is hardcoded for `"Philips FTV (NVIDIA High Definition Audio)"`.
> To use it with a different device, change `DEVICE_NAME` in `silentaudio.py` to match
> the exact name shown in your Windows audio devices list.

A tiny Windows background process that streams a near-inaudible tone to a
specific audio output device, so receivers / DACs / HDMI sinks don't power down for
lack of signal.

## How it works

- Waits for the target device to appear, then opens an `sd.OutputStream` at 48 kHz / 2 ch float32.
- Generates a 20 Hz sine wave at -90 dBFS (effectively silent, but a real,
  non-zero signal — some devices treat pure zeros as "no signal").
- Polls every 5 seconds; automatically recovers if the device disconnects and reconnects.
- Sends a Windows toast notification if the device is not found, if a different TV is
  connected instead, or if audio stops playing on the expected device.
- Runs forever; exits cleanly on `Ctrl+C` or when the process is killed.

## Run from source

```
python -m pip install -r requirements.txt
pythonw silentaudio.py        # no console window
```

Or just double-click `run.bat`.

## Build a standalone .exe

```
build.bat
```

Produces `dist\silentaudio.exe`. No Python required on the target machine.
The build uses `console=False`, so no terminal window appears.

## Autostart on login

Put a shortcut to `silentaudio.exe` in:

```
%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
```

(Press `Win+R`, paste `shell:startup`, Enter — drop the shortcut there.)

## Stopping it

It has no UI. Kill it from Task Manager (`silentaudio.exe` or `pythonw.exe`).
If you want a tray icon with Pause/Quit later, that's a small addition with
`pystray`.

## Notes

- Streams to the **named device only**, not the default output. Changing the
  default device in Windows has no effect.
- CPU and memory footprint are negligible.
