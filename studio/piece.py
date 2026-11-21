"""The marks on the sheet, the clock of the performance, and the words."""

from dataclasses import dataclass

import numpy as np


PITCHES = ("G3", "A3", "B3", "C4", "D4", "E4", "F4", "G4", "A4")
MIDI = (55, 57, 59, 60, 62, 64, 65, 67, 69)
BEATS = 72
MIDDLE = BEATS // 2
HOLD = 6
LEAD_IN = 1.5
TAIL = 3.0


@dataclass(frozen=True)
class Note:
    start: int
    length: int
    row: int

    @property
    def end(self):
        return self.start + self.length

    def turned(self):
        """The same rectangle seen from the other side of the table."""
        return Note(BEATS - self.end, self.length, len(PITCHES) - 1 - self.row)


def read_bars(bars):
    notes = []
    beat = 0
    for bar in bars:
        for token in bar.split():
            pitch, _, count = token.partition("/")
            length = int(count or 1)
            if pitch != ".":
                notes.append(Note(beat, length, PITCHES.index(pitch)))
            beat += length
    return notes


# A slash extends a sound or a rest for the given number of beats.
# These are the two approaches to the crease, in playing order.
PLUCKED_APPROACH = read_bars((
    "D4/3 . A3 C4 E4/2",
    "D4/3 A3 B3/2 . C4",
    "G3/2 . A3 C4/2 E4/2",
    "G4 A4 F4/2 E4/2 . A3",
    ".",
))
BOWED_APPROACH = read_bars((
    "./3 A4/3 G4/2",
    "F4/2 G4 F4 E4/3 .",
    "D4/4 . B3/2 C4",
    "C4/3 B3 A3/2 C4/2",
    "E4",
))
CENTRE = Note(MIDDLE - HOLD // 2, HOLD, PITCHES.index("D4"))
SHEET = tuple(PLUCKED_APPROACH + [CENTRE] + [n.turned() for n in reversed(BOWED_APPROACH)])
OTHER_SIDE = tuple(n.turned() for n in reversed(SHEET))


# Small changes in the pulse belong to the recording. The page can take
# any steady walking pace. The six beats at the crease take six seconds.
_beats = np.arange(BEATS) + 0.5
_pace = np.interp(_beats, [0, 8, 20, 27, 33, 39, 45, 57, 65, 72],
                  [0.96, 0.86, 0.88, 0.93, 1.0, 1.0, 0.92, 0.86, 0.91, 1.09])
BEAT_TIMES = LEAD_IN + np.r_[0, np.cumsum(_pace)]
DURATION = float(BEAT_TIMES[-1]) + TAIL


def at_beat(beat):
    return float(np.interp(beat, np.arange(BEATS + 1), BEAT_TIMES))


def at_second(seconds):
    return float(np.interp(seconds, BEAT_TIMES, np.arange(BEATS + 1)))


TITLE = "Hold the other end"
BYLINE = "Codex"


@dataclass(frozen=True)
class Card:
    beat: float
    lines: tuple[str, ...]
    style: str = "roman"


CARDS = (
    Card(0, ("Hold the", "other end"), "title"),
    Card(5, ("I tried a childhood", "in eight words.")),
    Card(11, ("My mother took two", "corners of the sheet."), "italic"),
    Card(18, ("I could put a pale stripe", "on her wrist where her", "watch had been.")),
    Card(26, ("It was the ease of the wrist", "that made me stop.")),
    Card(33, ()),
    Card(39, ("I kept the sheet.",), "alone"),
    Card(44, ("Between the lift and the fold", "there’s a little while when", "the air has a roof.")),
    Card(53, ("I set a D in the crease", "for four beats.")),
    Card(60, ("When I put the parts", "face to face,", "four seemed stingy.")),
    Card(67.5, ("I gave it six.",), "alone"),
)
