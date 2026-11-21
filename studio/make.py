"""Reprint the table score and perform the duet into the film."""

from pathlib import Path
import tempfile

from film import render_film, subtitles
from press import render_pdf
from sound import render_audio


ROOT = Path(__file__).resolve().parents[1]


def main():
    with tempfile.TemporaryDirectory(prefix=".table-duet-", dir=ROOT) as directory:
        temp = Path(directory)
        paper = temp / "hold-the-other-end.pdf"
        render_pdf(paper)
        wav = temp / "strings.wav"
        render_audio(wav)
        film = temp / "hold-the-other-end.mp4"
        cover = temp / "cover.jpg"
        render_film(wav, film, cover)
        captions = temp / "words.vtt"
        subtitles(captions)
        print_dir = ROOT / "output" / "pdf"
        recording_dir = ROOT / "recording"
        print_dir.mkdir(parents=True, exist_ok=True)
        recording_dir.mkdir(exist_ok=True)
        paper.replace(print_dir / paper.name)
        film.replace(recording_dir / film.name)
        cover.replace(recording_dir / cover.name)
        captions.replace(recording_dir / captions.name)


if __name__ == "__main__":
    main()
