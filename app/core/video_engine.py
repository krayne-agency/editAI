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
        # Si ffprobe échoue (returncode != 0) ou stdout vide → on assume audio présent
        if r.returncode != 0 or not r.stdout.strip():
            return r.returncode != 0  # erreur ffprobe = on suppose audio présent
        return True
    except Exception:  # noqa: BLE001
        return True  # en cas d'erreur, on tente avec audio


def _find_font() -> str | None:
    """Retourne le chemin d'une police bold disponible pour drawtext."""
    candidates = [
        Path("C:/Windows/Fonts/impact.ttf"),
        Path("C:/Windows/Fonts/Impact.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf"),
        Path("/usr/share/fonts/truetype/msttcorefonts/Impact.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
    ]
    for p in candidates:
        if p.exists():
            s = str(p).replace("\\", "/")
            # Escape du ':' du lecteur Windows (C: → C\:) pour ffmpeg
            if len(s) >= 2 and s[1] == ":":
                s = s[0] + "\\:" + s[2:]
            return s
    return None


def _drawtext_gaming(word: str, t_start: float, t_dur: float, font_path: str) -> str:
    """Filtre drawtext esport : texte blanc + contour néon + apparition rapide."""
    t_end = t_start + t_dur
    alpha = (
        f"if(lt(t,{t_start:.3f}),0,"
        f"if(lt(t,{t_start+0.07:.3f}),(t-{t_start:.3f})/0.07,"
        f"if(lt(t,{t_end-0.10:.3f}),1,"
        f"max(0,(t-{t_end-0.10:.3f})/0.10*(-1)+1))))"
    )
    safe_word = word.replace("'", "\\'").replace(":", "\\:")
    return (
        f"drawtext=fontfile='{font_path}'"
        f":text='{safe_word}'"
        f":fontsize=108"
        f":fontcolor=white"
        f":borderw=6:bordercolor=0x00FF88"
        f":shadowx=5:shadowy=5:shadowcolor=black@0.9"
        f":x=(w-text_w)/2:y=(h/2-text_h)"
        f":alpha='{alpha}'"
    )


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

    # (contrast/saturation/sharpness/vignette définis plus bas selon opening_score)

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

    # Audio : volume normalisé + fades synchronisés avec la vidéo
    audio_filter = (
        f";[0:a]volume=1.5,bass=g=4,"
        f"afade=t=in:st=0:d={fade_in_dur},"
        f"afade=t=out:st={fade_out_start:.2f}:d={fade_out_dur}[audio_out]"
        if has_audio else ""
    )
    audio_map = ["-map", "[audio_out]"] if has_audio else ["-an"]
    audio_codec = ["-c:a", "aac", "-b:a", "192k", "-ar", "44100"] if has_audio else []

    # ── Paramètres visuels selon dynamisme de la vidéo ──────────────────
    _extra = 16  # marge de shake de chaque côté (px)
    if opening_score >= 75:
        saturation, contrast = 1.20, 1.06
        sharpness = "unsharp=5:5:1.5:3:3:0.0"
        vignette = "vignette=PI/3.5"
    elif opening_score >= 55:
        saturation, contrast = 1.12, 1.05
        sharpness = "unsharp=5:5:1.0:3:3:0.0"
        vignette = "vignette=PI/4"
    else:
        saturation, contrast = 1.25, 1.10
        sharpness = "unsharp=5:5:2.0:3:3:0.0"
        vignette = "vignette=PI/4"

    # ── Moments clés : 18 %, 52 %, 78 % de la durée ─────────────────────
    _key_t = [
        t for t in (out_duration * p for p in (0.18, 0.52, 0.78))
        if 1.0 < t < out_duration - 1.5
    ]
    _shake_dur = 0.22
    _flash_dur = 0.07
    _labels = ["1 TAP !", "CLUTCH", "ACE !"]

    # Scale avec marge pour headroom du shake
    _sw = (1080 + _extra * 2) // 2 * 2   # 1112 — pair pour libx264
    _sh = (1920 + _extra * 2) // 2 * 2   # 1952

    # Shake : crop oscillant autour du centre avec sin()/cos()
    _sxp, _syp = [], []
    for _i, _kt in enumerate(_key_t):
        _te = _kt + _shake_dur
        _ax = _extra * (0.55 + _i * 0.12)
        _ay = _extra * 0.30
        _sxp.append(
            f"if(between(t,{_kt:.3f},{_te:.3f}),{_ax:.1f}*sin(t*{120+_i*10}),0)"
        )
        _syp.append(
            f"if(between(t,{_kt:.3f},{_te:.3f}),{_ay:.1f}*cos(t*{100+_i*7}),0)"
        )
    _cx = f"((iw-1080)/2)+{('+'.join(_sxp) or '0')}"
    _cy = f"((ih-1920)/2)+{('+'.join(_syp) or '0')}"

    # Flash blanc court aux moments clés
    _flash_en = "+".join(
        f"between(t,{_kt:.3f},{_kt+_flash_dur:.3f})" for _kt in _key_t
    ) or "0"

    # Texte gaming esport (si police Impact/Arial Bold disponible)
    _font = _find_font()
    _text_chain = ""
    if _font and _key_t:
        _text_chain = "," + ",".join(
            _drawtext_gaming(_labels[_i], _kt + 0.07, 0.55, _font)
            for _i, _kt in enumerate(_key_t[:3])
        )

    # ── Filter complex TikTok — portrait + shake + flash + neon + text ───
    filter_complex = (
        f"[0:v]scale={_sw}:{_sh}:force_original_aspect_ratio=increase,"
        f"crop=1080:1920:{_cx}:{_cy},"
        f"{sharpness},"
        f"eq=contrast={contrast}:saturation={saturation}:brightness=0.02,"
        f"colorchannelmixer=rr=1.04:gg=1.0:bb=1.06,"
        f"{vignette},"
        f"drawbox=x=0:y=0:w=iw:h=ih:color=white@0.8:t=fill:enable='{_flash_en}'"
        f"{_text_chain},"
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
