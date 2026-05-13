"""Silently stream a near-inaudible tone to keep the default audio output awake."""
from __future__ import annotations

import msvcrt
import os
import sys
import time

import threading

import numpy as np
import sounddevice as sd
from winotify import Notification

SAMPLE_RATE = 48_000
FREQUENCY_HZ = 20.0
AMPLITUDE = 10 ** (-90 / 20)
BLOCK_SIZE = 1024
CHANNELS = 2
DEVICE_NAME = "Philips FTV (NVIDIA High Definition Audio)"
LOCK_FILE = os.path.join(os.environ.get("TEMP", os.getcwd()), "silentaudio.lock")
RETRY_INTERVAL = 5
CALLBACK_TIMEOUT = 10.0  # seconds without a callback tick → assume post-sleep stall


def make_callback(error_event: threading.Event, last_tick: list):
    phase = 0.0
    phase_step = 2.0 * np.pi * FREQUENCY_HZ / SAMPLE_RATE

    def callback(outdata, frames, time_info, status):
        nonlocal phase
        last_tick[0] = time.monotonic()
        if status:
            error_event.set()
        n = np.arange(frames, dtype=np.float32)
        wave = (AMPLITUDE * np.sin(phase + phase_step * n)).astype(np.float32)
        phase = (phase + phase_step * frames) % (2.0 * np.pi)
        outdata[:] = np.repeat(wave[:, None], CHANNELS, axis=1)

    return callback


def acquire_single_instance():
    """Open the lock file exclusively. If already locked, kill the existing process and retry."""
    import ctypes
    import struct

    for _ in range(2):
        f = open(LOCK_FILE, "w+b")
        try:
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            f.write(struct.pack("I", os.getpid()))
            f.flush()
            return f  # caller must keep this alive
        except OSError:
            # Read the PID of the existing instance and kill it
            try:
                f.seek(0)
                data = f.read(4)
                if len(data) == 4:
                    pid = struct.unpack("I", data)[0]
                    handle = ctypes.windll.kernel32.OpenProcess(1, False, pid)
                    if handle:
                        ctypes.windll.kernel32.TerminateProcess(handle, 0)
                        ctypes.windll.kernel32.CloseHandle(handle)
            except Exception:
                pass
            f.close()
            time.sleep(0.3)

    raise RuntimeError("Could not acquire single-instance lock")


def find_device() -> int:
    for i, d in enumerate(sd.query_devices()):
        if d["max_output_channels"] > 0 and DEVICE_NAME in d["name"]:
            return i
    return -1


def other_tv_connected() -> bool:
    for d in sd.query_devices():
        if d["max_output_channels"] > 0 and "TV" in d["name"] and DEVICE_NAME not in d["name"]:
            return True
    return False


def toast(title: str, msg: str) -> None:
    Notification(app_id="silentaudio", title=title, msg=msg).show()


def wait_for_device() -> int:
    notified_missing = False
    notified_other = False
    while True:
        device = find_device()
        if device != -1:
            return device
        if not notified_missing:
            toast("Philips TV not found", "silentaudio is waiting for the Philips TV to connect.")
            notified_missing = True
        if not notified_other and other_tv_connected():
            toast("Different TV detected", "Philips TV not found but another TV is connected. You may want to re-assess silentaudio.")
            notified_other = True
        time.sleep(RETRY_INTERVAL)


def main() -> int:
    try:
        _lock = acquire_single_instance()  # must stay open to hold the lock
        while True:
            device = wait_for_device()
            try:
                error_event = threading.Event()
                last_tick = [time.monotonic()]
                with sd.OutputStream(
                    device=device,
                    samplerate=SAMPLE_RATE,
                    blocksize=BLOCK_SIZE,
                    channels=CHANNELS,
                    dtype="float32",
                    callback=make_callback(error_event, last_tick),
                ) as stream:
                    notified_wrong_device = False
                    while stream.active and not error_event.is_set():
                        if find_device() == -1:
                            break
                        if time.monotonic() - last_tick[0] > CALLBACK_TIMEOUT:
                            break  # callback stalled (e.g. after hibernate/sleep)
                        stream_device_name = sd.query_devices(stream.device)["name"]
                        if DEVICE_NAME not in stream_device_name and not notified_wrong_device:
                            toast("silentaudio misconfigured", "Audio is not playing on the expected Philips TV device.")
                            notified_wrong_device = True
                        time.sleep(RETRY_INTERVAL)
            except Exception:
                pass
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
