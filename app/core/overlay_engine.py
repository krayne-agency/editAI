"""
overlay_engine.py — Overlays animés sur vidéos TikTok.
Ajoute hook animé (fade-in) et sous-titres synchronisés via ffmpeg drawtext.
Aucune dépendance externe : ffmpeg uniquement.
"""
from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

# Polices Windows par ordre de préférence
_WINDOWS_FONTS = [
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/calibrib.ttf",
    "C:/Windows/Fonts/calibri.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
]


def _find_font() -> str:
    for fp in _WINDOWS_FONTS:
        if Path(fp).exists():
            return fp.replace("\\", "/")
    return ""


def _write_text_tmp(text: str) -> str:
    """Écrit le texte dans un fichier .txt temporaire (UTF-8). Retourne le chemin."""
    tf = tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    )
    tf.write(text)
    tf.close()
    return tf.name.replace("\\", "/")


def _run(cmd: list[str], timeout: int = 180) -> bool:
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=timeout)
        return r.returncode == 0
    except Exception:
        return False


# ── Hook animé ────────────────────────────────────────────────────────────────

def add_hook_overlay(
    video_path: str,
    output_path: str,
    hook: str,
    ffmpeg_bin: str,
) -> bool:
    """
    Ajoute le texte du hook avec fade-in en haut de la vidéo (0.3s → 0.8s).
    Fond semi-transparent noir derrière le texte.
    Retourne True si succès.
    """
    font = _find_font()
    txt_file = _write_text_tmp(hook[:80])  # max 80 chars

    font_part = f":fontfile='{font}'" if font else ""

    vf = (
        f"drawtext=textfile='{txt_file}'"
        f"{font_part}"
        ":fontcolor=white"
        ":fontsize=52"
        ":x=(w-text_w)/2"
        ":y=h*0.10"
        ":alpha='if(lt(t,0.3),0,if(lt(t,0.8),(t-0.3)/0.5,1))'"
        ":box=1:boxcolor=black@0.55:boxborderw=14"
    )

    success = _run([
        ffmpeg_bin, "-y",
        "-i", video_path,
        "-vf", vf,
        "-c:a", "copy",
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        output_path,
    ])

    # Nettoyage fichier temporaire
    try:
        Path(txt_file).unlink(missing_ok=True)
    except Exception:
        pass

    return success


# ── Sous-titres ───────────────────────────────────────────────────────────────

def add_subtitles_overlay(
    video_path: str,
    output_path: str,
    voiceover_script: str,
    ffmpeg_bin: str,
) -> bool:
    """
    Parse le script [0s] / [2s] ... et affiche chaque ligne en bas de l'image.
    Retourne True si succès.
    """
    lines = re.findall(r"\[(\d+)s\]\s*(.+)", voiceover_script)
    if not lines:
        return False

    font = _find_font()
    font_part = f":fontfile='{font}'" if font else ""

    filters: list[str] = []
    tmp_files: list[str] = []

    for i, (start_s, text) in enumerate(lines):
        start = int(start_s)
        end = int(lines[i + 1][0]) - 0 if i + 1 < len(lines) else start + 3
        line_text = text.strip()[:70]

        txt_file = _write_text_tmp(line_text)
        tmp_files.append(txt_file)

        f = (
            f"drawtext=textfile='{txt_file}'"
            f"{font_part}"
            ":fontcolor=white"
            ":fontsize=40"
            ":x=(w-text_w)/2"
            ":y=h*0.82"
            f":enable='between(t,{start},{end})'"
            ":box=1:boxcolor=black@0.60:boxborderw=10"
        )
        filters.append(f)

    vf = ",".join(filters)

    success = _run([
        ffmpeg_bin, "-y",
        "-i", video_path,
        "-vf", vf,
        "-c:a", "copy",
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        output_path,
    ])

    for tf in tmp_files:
        try:
            Path(tf).unlink(missing_ok=True)
        except Exception:
            pass

    return success
