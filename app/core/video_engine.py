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

    # TikTok : fond flouté 9:16 + vidéo originale centrée par-dessus (pas de crop brutal)
    filter_complex = (
        f"[0:v]split=2[raw1][raw2];"
        f"[raw1]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
        f"boxblur=20:5,eq=contrast={contrast}:saturation={saturation}[bg];"
        f"[raw2]scale=1080:1920:force_original_aspect_ratio=decrease,"
        f"eq=contrast={contrast}:saturation={saturation}[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2[out]"
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
        "-af",
        f"loudnorm=I={loudnorm_target}:TP=-1.5:LRA=11",
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
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-ar",
        "44100",
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
        "adaptation_notes": (
            "9:16 1080x1920, 30fps, audio normalise, coupe max 35s, "
            f"trim intro: {start_trim:.2f}s, score ouverture: {opening_score}/100"
        ),
    }
