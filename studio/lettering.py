"""Shared inks and the two cuts of type used for both editions."""

import os
from pathlib import Path
import subprocess


PAPER = (247, 244, 234)
INK = (36, 43, 40)
RUSSET = (148, 58, 38)
PINE = (45, 88, 79)
QUIET = (88, 91, 79)


def serif(italic=False):
    override = os.environ.get("DUET_ITALIC" if italic else "DUET_ROMAN")
    if override:
        return Path(override)
    face = "STIX Two Text"
    style = "Italic" if italic else "Regular"
    mac_name = "STIXTwoText-Italic.ttf" if italic else "STIXTwoText.ttf"
    mac = Path("/System/Library/Fonts/Supplemental") / mac_name
    if mac.is_file():
        return mac
    found = subprocess.check_output(
        ["fc-match", "-f", "%{file}", f"{face}:style={style}"], text=True,
    )
    return Path(found)
