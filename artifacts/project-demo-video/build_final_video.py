from __future__ import annotations

import asyncio
import math
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import edge_tts
import imageio_ffmpeg
from mutagen.mp3 import MP3


ROOT = Path(__file__).resolve().parent
SRT_PATH = ROOT / "narration.srt"
CUT_VIDEO = ROOT / "project-demo-cut.mp4"
TTS_DIR = ROOT / "edge-tts"
NARRATION_WAV = ROOT / "narration.wav"
FINAL_VIDEO = ROOT / "project-demo-final.mp4"
VOICE = "zh-CN-XiaoxiaoNeural"


@dataclass(frozen=True)
class Cue:
    index: int
    start: float
    end: float
    text: str

    @property
    def duration(self) -> float:
        return self.end - self.start


def parse_timestamp(value: str) -> float:
    hours, minutes, rest = value.split(":")
    seconds, millis = rest.split(",")
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(millis) / 1000


def parse_srt(path: Path) -> list[Cue]:
    blocks = re.split(r"\r?\n\s*\r?\n", path.read_text(encoding="utf-8").strip())
    cues: list[Cue] = []
    for block in blocks:
        lines = block.splitlines()
        if len(lines) < 3:
            continue
        start_text, end_text = (part.strip() for part in lines[1].split("-->", 1))
        cues.append(
            Cue(
                index=int(lines[0]),
                start=parse_timestamp(start_text),
                end=parse_timestamp(end_text),
                text=" ".join(line.strip() for line in lines[2:] if line.strip()),
            )
        )
    if not cues:
        raise RuntimeError("No subtitle cues were parsed")
    return cues


async def synthesize_cue(cue: Cue) -> Path:
    TTS_DIR.mkdir(parents=True, exist_ok=True)
    output = TTS_DIR / f"cue-{cue.index:02d}.mp3"
    target = max(1.0, cue.duration - 0.35)
    if output.exists():
        actual = MP3(output).info.length
        if actual <= target:
            print(
                f"cue {cue.index:02d}: reusing {actual:.2f}s / "
                f"{cue.duration:.2f}s"
            )
            return output
    rate = 0
    for _ in range(6):
        await edge_tts.Communicate(
            cue.text,
            VOICE,
            rate=f"+{rate}%",
            volume="+0%",
            pitch="+0Hz",
        ).save(str(output))
        actual = MP3(output).info.length
        if actual <= target:
            print(
                f"cue {cue.index:02d}: {actual:.2f}s / {cue.duration:.2f}s, rate +{rate}%"
            )
            return output
        required = math.ceil((actual / target - 1) * 100)
        rate = min(90, max(rate + 10, required + rate))
    raise RuntimeError(
        f"Cue {cue.index} remains too long after rate adjustment: "
        f"{MP3(output).info.length:.2f}s > {target:.2f}s"
    )


def run(command: list[str], *, cwd: Path = ROOT) -> None:
    print("Running:", " ".join(command))
    subprocess.run(command, cwd=cwd, check=True)


def build_aligned_narration(ffmpeg: str, cues: list[Cue], files: list[Path]) -> None:
    command = [ffmpeg, "-y", "-hide_banner"]
    for file in files:
        command.extend(["-i", str(file)])

    filters: list[str] = []
    mixed_inputs: list[str] = []
    for input_index, cue in enumerate(cues):
        label = f"a{input_index}"
        delay_ms = round(cue.start * 1000)
        filters.append(
            f"[{input_index}:a]"
            "silenceremove=start_periods=1:start_duration=0.03:start_threshold=-45dB,"
            f"adelay={delay_ms}:all=1[{label}]"
        )
        mixed_inputs.append(f"[{label}]")

    total_duration = cues[-1].end
    filters.append(
        "".join(mixed_inputs)
        + f"amix=inputs={len(cues)}:duration=longest:normalize=0,"
        + f"apad,atrim=0:{total_duration},aresample=48000[aout]"
    )
    command.extend(
        [
            "-filter_complex",
            ";".join(filters),
            "-map",
            "[aout]",
            "-c:a",
            "pcm_s16le",
            str(NARRATION_WAV),
        ]
    )
    run(command)


def build_final_video(ffmpeg: str) -> None:
    filter_listing = subprocess.run(
        [ffmpeg, "-hide_banner", "-filters"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    if " subtitles " not in filter_listing:
        raise RuntimeError("The downloaded ffmpeg build does not include the subtitles filter")

    subtitle_filter = (
        "subtitles=filename='narration.srt':"
        "force_style='FontName=Microsoft YaHei,FontSize=14,"
        "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
        "BackColour=&HAA000000,BorderStyle=3,Outline=1,Shadow=0,"
        "Alignment=2,MarginV=42'"
    )
    audio_filter = (
        "[0:a]volume=0.08[original];"
        "[1:a]volume=1.25[voice];"
        "[original][voice]amix=inputs=2:duration=first:dropout_transition=0[aout]"
    )
    run(
        [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-i",
            CUT_VIDEO.name,
            "-i",
            NARRATION_WAV.name,
            "-filter_complex",
            audio_filter,
            "-vf",
            subtitle_filter,
            "-map",
            "0:v:0",
            "-map",
            "[aout]",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            FINAL_VIDEO.name,
        ]
    )


async def main() -> None:
    if not CUT_VIDEO.exists():
        raise FileNotFoundError(CUT_VIDEO)
    cues = parse_srt(SRT_PATH)
    files = [await synthesize_cue(cue) for cue in cues]
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    build_aligned_narration(ffmpeg, cues, files)
    build_final_video(ffmpeg)
    print(f"Final video: {FINAL_VIDEO}")


if __name__ == "__main__":
    asyncio.run(main())
