from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class OpeningAnalysis:
    duration_sec: float
    width: int
    height: int
    fps: float
    black_intro_sec: float
    mean_volume_db: float
    opening_score: int
    recommendations: list[str]


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True)


def _probe_video(ffprobe_bin: str, input_path: Path) -> tuple[float, int, int, float]:
    cmd = [
        ffprobe_bin,
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,r_frame_rate:format=duration",
        "-of",
        "json",
        str(input_path),
    ]
    result = _run(cmd)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ffprobe error")

    payload = json.loads(result.stdout)
    stream = payload.get("streams", [{}])[0]
    fmt = payload.get("format", {})

    width = int(stream.get("width", 0) or 0)
    height = int(stream.get("height", 0) or 0)
    duration_sec = float(fmt.get("duration", 0.0) or 0.0)

    fps_raw = str(stream.get("r_frame_rate", "30/1"))
    if "/" in fps_raw:
        num, den = fps_raw.split("/", 1)
        den_v = float(den or 1)
        fps = float(num or 30) / (den_v if den_v != 0 else 1)
    else:
        fps = float(fps_raw or 30)

    return duration_sec, width, height, fps


def _detect_black_intro(ffmpeg_bin: str, input_path: Path) -> float:
    cmd = [
        ffmpeg_bin,
        "-hide_banner",
        "-v",
        "info",
        "-t",
        "3",
        "-i",
        str(input_path),
        "-vf",
        "blackdetect=d=0.10:pix_th=0.10",
        "-an",
        "-f",
        "null",
        "NUL",
    ]
    result = _run(cmd)
    stderr = result.stderr

    starts = [float(v) for v in re.findall(r"black_start:([0-9.]+)", stderr)]
    ends = [float(v) for v in re.findall(r"black_end:([0-9.]+)", stderr)]

    if not starts or not ends:
        return 0.0

    first_start = starts[0]
    first_end = ends[0]
    if first_start <= 0.20:
        return round(max(0.0, first_end - first_start), 2)
    return 0.0


def _detect_mean_volume(ffmpeg_bin: str, input_path: Path) -> float:
    cmd = [
        ffmpeg_bin,
        "-hide_banner",
        "-v",
        "info",
        "-t",
        "3",
        "-i",
        str(input_path),
        "-af",
        "volumedetect",
        "-vn",
        "-f",
        "null",
        "NUL",
    ]
    result = _run(cmd)
    stderr = result.stderr
    match = re.search(r"mean_volume:\s*(-?[0-9.]+) dB", stderr)
    if not match:
        return -20.0
    return float(match.group(1))


def analyze_opening(
    input_path: Path,
    ffmpeg_bin: str,
    ffprobe_bin: str,
) -> OpeningAnalysis:
    duration_sec, width, height, fps = _probe_video(ffprobe_bin, input_path)
    black_intro_sec = _detect_black_intro(ffmpeg_bin, input_path)
    mean_volume_db = _detect_mean_volume(ffmpeg_bin, input_path)

    score = 85
    recommendations: list[str] = []

    if black_intro_sec > 0.20:
        score -= 20
        recommendations.append("Retirer l'intro noire pour capter plus vite.")

    if mean_volume_db < -22:
        score -= 12
        recommendations.append("Audio faible en ouverture: renforcer le niveau sonore.")

    if duration_sec > 45:
        score -= 8
        recommendations.append("Durée longue: garder une version courte pour maximiser la rétention.")

    if (width / max(height, 1)) > 1.0:
        score -= 6
        recommendations.append("Source horizontale: recadrage vertical recommandé (9:16).")

    if fps < 23:
        score -= 4
        recommendations.append("Framerate bas: stabiliser à 30 fps.")

    score = max(35, min(score, 98))
    if not recommendations:
        recommendations.append("Ouverture déjà solide, conserver le rythme actuel.")

    return OpeningAnalysis(
        duration_sec=round(duration_sec, 2),
        width=width,
        height=height,
        fps=round(fps, 2),
        black_intro_sec=black_intro_sec,
        mean_volume_db=round(mean_volume_db, 2),
        opening_score=score,
        recommendations=recommendations,
    )


def analysis_to_dict(analysis: OpeningAnalysis) -> dict[str, object]:
    return {
        "duration_sec": analysis.duration_sec,
        "width": analysis.width,
        "height": analysis.height,
        "fps": analysis.fps,
        "black_intro_sec": analysis.black_intro_sec,
        "mean_volume_db": analysis.mean_volume_db,
        "opening_score": analysis.opening_score,
        "recommendations": analysis.recommendations,
    }
