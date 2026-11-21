"""Two small string instruments. Everything in the recording starts here."""

from pathlib import Path
import wave

import numpy as np

from piece import BEATS, CENTRE, DURATION, MIDI, OTHER_SIDE, SHEET, at_beat


RATE = 44100
TAU = 2 * np.pi


def slow_noise(t, rate, rng):
    """A continuous, gently wandering control signal."""
    knots = np.arange(-1, int(t[-1] * rate) + 3)
    return np.interp(t * rate, knots, rng.standard_normal(len(knots)))


def pluck(frequency, length, weight, rng):
    t = np.arange(round((length + 0.32) * RATE)) / RATE
    # A string pulled a little to one side. The upper modes give up their
    # energy sooner. A second, weak set of modes belongs to the soundboard.
    place = rng.uniform(0.145, 0.188)
    strike = 0.00011 * (1 - np.exp(-30 * t))
    y = np.zeros_like(t)
    for n in range(1, 27):
        pitch = frequency * n * np.sqrt(1 + 0.000049 * n * n)
        strength = np.sin(np.pi * n * place) / (n ** 1.48 * np.sin(np.pi * place))
        decay = (0.41 + 0.29 * n ** 0.78) * (frequency / 294) ** 0.22
        phase = TAU * pitch * (t + strike)
        direct = np.cos(phase)
        coupled = 0.19 * np.cos(phase * 0.99915 + 0.13)
        y += strength * (direct + coupled) * np.exp(-t * decay)

    pick = rng.standard_normal(len(t))
    pick = np.convolve(pick, np.ones(13) / 13, mode="same")
    y += 0.10 * pick * np.exp(-t * 75)
    release = np.exp(-np.maximum(t - length, 0) * 22)
    return weight * 0.38 * y * (-np.expm1(-t * 190)) * release


def bow(frequency, length, weight, rng):
    t = np.arange(round((length + 0.46) * RATE)) / RATE
    # The string takes a moment to speak. The bow changes speed and pressure
    # on scales slower than a note, particularly on the long central D.
    vibrato_rate = rng.uniform(4.65, 5.1)
    vibrato = np.sin(TAU * vibrato_rate * t + 0.18 * np.sin(4.1 * t))
    cents = 4.6 * vibrato * (1 - np.exp(-t * 3)) + 1.6 * slow_noise(t, 3.0, rng)
    cents -= 4.0 * np.exp(-t * 15)
    phase = TAU / RATE * np.cumsum(frequency * np.exp2(cents / 1200))

    pressure = slow_noise(t, 4.5, rng)
    y = np.zeros_like(t)
    for n in range(1, 19):
        hz = n * frequency
        body = 0.52 + 0.61 * np.exp(-((hz - 550) / 270) ** 2)
        body += 0.40 * np.exp(-((hz - 1250) / 460) ** 2)
        body += 0.23 * np.exp(-((hz - 2250) / 520) ** 2)
        strength = body / n ** 1.42
        phase_offset = 0.23 * np.sin(1.67 * n)
        onset = 1 - np.exp(-t * (16.2 - min(n, 13) * 0.66))
        y += strength * np.sin(n * phase + phase_offset) * onset * (1 + 0.027 * pressure)

    hair = rng.standard_normal(len(t))
    hair = np.convolve(hair, np.ones(8) / 8, mode="same")
    hair -= np.convolve(hair, np.ones(47) / 47, mode="same")
    y += hair * (0.023 + 0.07 * np.exp(-t * 8)) * (1 - np.exp(-t * 40))
    attack = 1 - np.exp(-t * 10.0)
    bloom = 0.81 + 0.19 * np.sin(np.pi * np.minimum(t / length, 1))
    release = np.exp(-np.maximum(t - length, 0) * 13)
    return weight * 0.55 * y * attack * bloom * release


def play_part(notes, instrument, seed):
    rng = np.random.default_rng(seed)
    part = np.zeros(round(DURATION * RATE))
    for note in notes:
        hz = 440 * 2 ** ((MIDI[note.row] - 69) / 12)
        time = at_beat(note.start)
        onset = time if note == CENTRE else time + rng.uniform(-0.012, 0.012)
        length = at_beat(note.end) - time
        phrase = 0.92 + 0.095 * np.sin(np.pi * note.start / BEATS)
        weight = phrase * rng.uniform(0.92, 1.03)
        if note.length == 1:
            weight *= 0.87
        if note == CENTRE:
            weight *= 0.86
        sound = instrument(hz, length, weight, rng)
        start = round(onset * RATE)
        part[start:start + len(sound)] += sound
    return part


def room(signal, seed):
    rng = np.random.default_rng(seed)
    t = np.arange(round(1.55 * RATE)) / RATE
    impulse = rng.normal(0, 1, len(t)) * np.exp(-5.8 * t) * (1 - np.exp(-30 * t))
    impulse = np.convolve(impulse, np.ones(11) / 11, mode="same")
    impulse *= 0.12 / np.linalg.norm(impulse)
    for delay, amplitude in [(0.019, 0.065), (0.033, 0.042), (0.051, -0.031), (0.072, 0.023)]:
        index = int(RATE * (delay + rng.uniform(-0.002, 0.002)))
        impulse[index] += amplitude
    size = 1 << (len(signal) + len(impulse) - 2).bit_length()
    return np.fft.irfft(np.fft.rfft(signal, size) * np.fft.rfft(impulse, size), size)[:len(signal)]


def render_audio(path):
    plucked = play_part(SHEET, pluck, 37)
    bowed = play_part(OTHER_SIDE, bow, 83)
    centre = (plucked + bowed) / 2
    left = plucked * 0.89 + bowed * 0.49 + room(centre, 30)
    right = plucked * 0.50 + bowed * 0.86 + room(centre, 71)
    stereo = np.column_stack((left, right))
    stereo *= 0.83 / np.max(np.abs(stereo))
    with wave.open(str(Path(path)), "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(RATE)
        output.writeframes(np.rint(stereo * 32767).astype("<i2").tobytes())
