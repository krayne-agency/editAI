from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any


class VideoProcessingError(RuntimeError):
    pass


def ffmpeg_available() -> bool:
    return resolve_ffmpeg_binary() is not None


def _pyinstaller_bundle_dir() -> Path | None:
    """Retourne le dossier _internal quand l'app tourne comme exe PyInstaller."""
    import sys as _sys
    if getattr(_sys, "frozen", False):
        return Path(getattr(_sys, "_MEIPASS", Path(_sys.executable).parent))
    return None


def resolve_ffmpeg_binary() -> str | None:
    # 1. Binaire embarqué dans le build PyInstaller (_internal/)
    bundle = _pyinstaller_bundle_dir()
    if bundle:
        candidate = bundle / "ffmpeg.exe"
        if candidate.exists():
            return str(candidate)

    # 2. PATH système
    direct = shutil.which("ffmpeg")
    if direct:
        return direct

    # 3. imageio-ffmpeg (bundlé via pip, fonctionne sur tout PC)
    try:
        import imageio_ffmpeg  # type: ignore[import]
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and Path(exe).exists():
            return exe
    except Exception:
        pass

    # 4. Installation winget (PATH pas encore rechargé)
    winget_root = Path.home() / "AppData" / "Local" / "Microsoft" / "WinGet" / "Packages"
    if winget_root.exists():
        matches = sorted(winget_root.glob("**/ffmpeg.exe"))
        if matches:
            return str(matches[-1])

    return None


def resolve_ffprobe_binary() -> str | None:
    # 1. Binaire embarqué dans le build PyInstaller (_internal/)
    bundle = _pyinstaller_bundle_dir()
    if bundle:
        candidate = bundle / "ffprobe.exe"
        if candidate.exists():
            return str(candidate)

    # 2. PATH système
    direct = shutil.which("ffprobe")
    if direct:
        return direct

    # 3. Installation winget
    winget_root = Path.home() / "AppData" / "Local" / "Microsoft" / "WinGet" / "Packages"
    if winget_root.exists():
        matches = sorted(winget_root.glob("**/ffprobe.exe"))
        if matches:
            return str(matches[-1])

    return None


def _get_video_duration(input_path: Path, ffprobe_bin: str | None) -> float:
    """Retourne la durée en secondes via ffprobe, ou 35.0 par défaut."""
    if not ffprobe_bin:
        return 35.0
    try:
        r = subprocess.run(
            [
                ffprobe_bin, "-v", "quiet",
                "-show_entries", "format=duration",
                "-of", "csv=p=0",
                str(input_path),
            ],
            capture_output=True, text=True, timeout=8,
        )
        return float(r.stdout.strip())
    except Exception:  # noqa: BLE001
        return 35.0


def _has_audio_stream(input_path: Path, ffprobe_bin: str | None) -> bool:
    """Retourne True si la vidéo source possède une piste audio."""
    if not ffprobe_bin:
        return True  # on suppose oui si ffprobe absent
    try:
        r = subprocess.run(
            [
                ffprobe_bin, "-v", "quiet",
                "-select_streams", "a:0",
                "-show_entries", "stream=codec_type",
                "-of", "csv=p=0",
                str(input_path),
            ],
            capture_output=True, text=True, timeout=8,
        )
        return bool(r.stdout.strip())
    except Exception:  # noqa: BLE001
        return True  # en cas d'erreur, on tente avec audio


def prepare_tiktok_video(
    input_path: Path,
    output_dir: Path,
    opening_analysis: dict[str, Any] | None = None,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)

    if not input_path.exists():
        raise VideoProcessingError(f"Fichier introuvable: {input_path}")

    ffmpeg_bin = resolve_ffmpeg_binary()
    if not ffmpeg_bin:
        raise VideoProcessingError(
            "ffmpeg introuvable. Installe ffmpeg puis relance l'application."
        )

    processed_path = output_dir / f"{input_path.stem}_tiktok_ready.mp4"
    thumbnail_path = output_dir / f"{input_path.stem}_thumbnail.jpg"

    black_intro_sec = 0.0
    opening_score = 80
    mean_volume_db = -20.0
    if opening_analysis:
        black_intro_sec = float(opening_analysis.get("black_intro_sec", 0.0) or 0.0)
        opening_score = int(opening_analysis.get("opening_score", 80) or 80)
        mean_volume_db = float(opening_analysis.get("mean_volume_db", -20.0) or -20.0)

    start_trim = min(max(black_intro_sec, 0.0), 1.5)

    contrast = 1.03
    saturation = 1.06
    if opening_score < 65:
        contrast = 1.08
        saturation = 1.12

    loudnorm_target = "-16"
    if mean_volume_db < -24:
        loudnorm_target = "-14"

    # Détection piste audio
    ffprobe_bin = resolve_ffprobe_binary()
    has_audio = _has_audio_stream(input_path, ffprobe_bin)

    # Durée réelle de sortie (capée à 35s, en tenant compte du trim)
    raw_duration = _get_video_duration(input_path, ffprobe_bin)
    out_duration = min(raw_duration - start_trim, 35.0)
    fade_in_dur = 0.5
    fade_out_dur = 1.5
    # Fade-out : commence 1.5s avant la fin réelle
    fade_out_start = max(out_duration - fade_out_dur, fade_in_dur + 1.0)

    # Audio normalisé + fades audio dans le filter_complex (compatible -map explicite)
    audio_filter = (
        f";[0:a]loudnorm=I={loudnorm_target}:TP=-1.5:LRA=11,"
        f"afade=t=in:st=0:d={fade_in_dur},"
        f"afade=t=out:st={fade_out_start:.2f}:d={fade_out_dur}[audio_out]"
        if has_audio else ""
    )
    audio_map = ["-map", "[audio_out]"] if has_audio else ["-an"]
    audio_codec = ["-c:a", "aac", "-b:a", "192k", "-ar", "44100"] if has_audio else []

    # TikTok portrait : scale pour remplir 1080×1920, puis zoom ×1.35 avec
    # recadrage centré légèrement vers le bas (zone arme en FPS)
    _zoom = 1.35
    _zw = int(1080 * _zoom) // 2 * 2   # ex. 1458 (pair, obligatoire pour libx264)
    _zh = int(1920 * _zoom) // 2 * 2   # ex. 2592
    filter_complex = (
        f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
        f"scale={_zw}:{_zh},"
        f"crop=1080:1920:(iw-1080)/2:(ih-1920)*3/5,"
        f"eq=contrast={contrast}:saturation={saturation},"
        f"fade=t=in:st=0:d={fade_in_dur},"
        f"fade=t=out:st={fade_out_start:.2f}:d={fade_out_dur}[out]"
        f"{audio_filter}"
    )

    process_cmd = [
        ffmpeg_bin,
        "-y",
        "-ss",
        f"{start_trim:.2f}",
        "-i",
        str(input_path),
        "-t",
        "35",
        "-filter_complex",
        filter_complex,
        "-map",
        "[out]",
        *audio_map,
        "-r",
        "30",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        *audio_codec,
        str(processed_path),
    ]

    thumb_cmd = [
        ffmpeg_bin,
        "-y",
        "-i",
        str(processed_path),
        "-ss",
        "00:00:01.000",
        "-vframes",
        "1",
        str(thumbnail_path),
    ]

    process_result = subprocess.run(process_cmd, capture_output=True, text=True)
    if process_result.returncode != 0:
        raise VideoProcessingError(
            "Erreur traitement vidéo ffmpeg:\n" + process_result.stderr[-1200:]
        )

    thumb_result = subprocess.run(thumb_cmd, capture_output=True, text=True)
    if thumb_result.returncode != 0:
        raise VideoProcessingError(
            "Erreur génération miniature ffmpeg:\n" + thumb_result.stderr[-1200:]
        )

    return {
        "processed_video": str(processed_path),
        "thumbnail": str(thumbnail_path),
        "has_audio": has_audio,
        "out_duration": round(out_duration, 1),
        "adaptation_notes": (
            "9:16 1080x1920, 30fps, "
            + ("son conservé + normalisé, " if has_audio else "aucune piste audio, ")
            + f"fade-in {fade_in_dur}s + fade-out {fade_out_dur}s (boucle TikTok), "
            + f"coupe max 35s, trim intro: {start_trim:.2f}s, score ouverture: {opening_score}/100"
        ),
    }
