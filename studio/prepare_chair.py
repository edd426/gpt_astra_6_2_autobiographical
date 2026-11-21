"""Make the offline sampler and the six-note parts for The other chair."""

import base64
import json
from pathlib import Path

import numpy as np

from piece import CENTRE, MIDI, OTHER_SIDE, PITCHES, SHEET
from sound import RATE, bow, pluck


SAMPLE_RATE = RATE // 2
ROOT = Path(__file__).resolve().parents[1]


def approach(notes):
    phrase = [note for note in notes if note.start <= CENTRE.start][-6:]
    return [
        dict(pitch=PITCHES[n.row], midi=MIDI[n.row], beat=n.start - phrase[0].start, length=n.length)
        for n in phrase
    ]


def half_rate(signal):
    x = np.arange(-32, 33)
    kernel = 0.46 * np.sinc(0.46 * x) * np.blackman(len(x))
    return np.convolve(signal, kernel / sum(kernel), mode="same")[::2]


def encode(signal):
    pcm = np.rint(np.clip(signal, -1, 1) * 32767).astype("<i2")
    return base64.b64encode(pcm.tobytes()).decode("ascii")


def main():
    hz = 440 * 2 ** ((62 - 69) / 12)
    nail = half_rate(pluck(hz, 9, 0.93, np.random.default_rng(37)))
    hair = half_rate(bow(hz, 6, 0.96, np.random.default_rng(83)))

    # Crossfade into an earlier bow stroke, matching the phase of the D
    # before the turn. The player can keep drawing this note indefinitely.
    loop_in = round(1.30 * SAMPLE_RATE)
    approximate_end = round(4.23 * SAMPLE_RATE)
    period = round(SAMPLE_RATE / hz)
    candidates = range(approximate_end - period, approximate_end + period)
    reference = hair[loop_in - 160:loop_in + 160]
    loop_out = min(candidates, key=lambda j: np.mean((hair[j - 160:j + 160] - reference) ** 2))
    width = round(0.20 * SAMPLE_RATE)
    mix = np.sin(np.linspace(0, np.pi / 2, width)) ** 2
    hair[loop_out - width:loop_out] = (
        (1 - mix) * hair[loop_out - width:loop_out] + mix * hair[loop_in - width:loop_in]
    )
    bank = dict(
        rate=SAMPLE_RATE, root=62, loopIn=loop_in, loopOut=loop_out,
        parts=dict(pluck=approach(SHEET), bow=approach(OTHER_SIDE)),
        strings=dict(pluck=encode(nail), bow=encode(hair[:loop_out])),
    )
    target = ROOT / "other-chair" / "strings.js"
    target.write_text(
        "// Instrument data from studio/prepare_chair.py\nconst chairBank = "
        + json.dumps(bank, separators=(",", ":")) + ";\n",
        encoding="ascii",
    )


if __name__ == "__main__":
    main()
