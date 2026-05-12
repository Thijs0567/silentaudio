"""Silently stream a near-inaudible tone to keep the default audio output awake."""
from __future__ import annotations

import sys
import time

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 48_000
FREQUENCY_HZ = 20.0
AMPLITUDE = 10 ** (-90 / 20)
BLOCK_SIZE = 1024
CHANNELS = 2


def make_callback():
    phase = 0.0
    phase_step = 2.0 * np.pi * FREQUENCY_HZ / SAMPLE_RATE

    def callback(outdata, frames, time_info, status):
        nonlocal phase
        n = np.arange(frames, dtype=np.float32)
        wave = (AMPLITUDE * np.sin(phase + phase_step * n)).astype(np.float32)
        phase = (phase + phase_step * frames) % (2.0 * np.pi)
        outdata[:] = np.repeat(wave[:, None], CHANNELS, axis=1)

    return callback


def main() -> int:
    try:
        with sd.OutputStream(
            samplerate=SAMPLE_RATE,
            blocksize=BLOCK_SIZE,
            channels=CHANNELS,
            dtype="float32",
            callback=make_callback(),
        ):
            while True:
                time.sleep(3600)
    except KeyboardInterrupt:
        return 0
    except Exception:
        return 1


if __name__ == "__main__":
    sys.exit(main())
