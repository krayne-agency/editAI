"""
music_engine.py — Musique de fond pour vidéos TikTok.
Scanne workspace_data/music/, sélectionne selon le ton/niche, mixe via ffmpeg.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

_MUSIC_DIR = Path(__file__).resolve().parents[2] / "workspace_data" / "music"

# Association ton → mots-clés cherchés dans le nom du fichier
_TONE_KEYWORDS: dict[str, list[str]] = {
    "dynamique": ["hype", "energy", "dynamic", "fast", "trap", "drill", "bounce"],
    "expert":    ["focus", "ambient", "clean", "minimal", "lofi", "lo-fi", "study"],
    "amical":    ["happy", "fun", "chill", "vibe", "bright", "upbeat", "pop"],
    "premium":   ["luxury", "elegant", "cinematic", "epic", "dramatic", "piano"],
}


# ── Bibliothèque ──────────────────────────────────────────────────────────────

def get_music_library() -> list[Path]:
    """Retourne les fichiers audio présents dans workspace_data/music/."""
    _MUSIC_DIR.mkdir(parents=True, exist_ok=True)
    ext = {".mp3", ".wav", ".aac", ".m4a", ".ogg", ".flac"}
    return sorted(f for f in _MUSIC_DIR.iterdir() if f.suffix.lower() in ext)


def select_music(tone: str = "", niche: str = "") -> Path | None:
    """
    Retourne le fichier le plus adapté au ton/niche via score de mots-clés.
    Retourne None si la bibliothèque est vide.
    """
    library = get_music_library()
    if not library:
        return None

    keywords = _TONE_KEYWORDS.get(tone.lower(), [])
    niche_words = [w.lower() for w in niche.replace(",", " ").split() if len(w) > 2]
    all_keywords = keywords + niche_words

    best: Path | None = None
    best_score = -1
    for f in library:
        name = f.stem.lower()
        score = sum(1 for kw in all_keywords if kw in name)
        if score > best_score:
            best_score = score
            best = f

    return best  # en cas d'égalité (0), retourne le premier par ordre alphabétique


# ── Mixage ────────────────────────────────────────────────────────────────────

def mix_music(
    video_path: str,
    music_path: str,
    output_path: str,
    ffmpeg_bin: str,
    music_volume_db: float = -20.0,
) -> bool:
    """
    Mixe la musique en boucle sur la vidéo.
    music_volume_db : -30 = très discret, -10 = présent, -5 = fort
    La musique boucle automatiquement et s'arrête avec la vidéo.
    """
    # -stream_loop -1 boucle la musique indéfiniment → -shortest coupe au fin vidéo
    cmd = [
        ffmpeg_bin, "-y",
        "-i", video_path,
        "-stream_loop", "-1", "-i", music_path,
        "-filter_complex",
        (
            f"[1:a]volume={music_volume_db}dB[music];"
            "[0:a][music]amix=inputs=2:duration=first:dropout_transition=1[aout]"
        ),
        "-map", "0:v",
        "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        output_path,
    ]

    try:
        r = subprocess.run(cmd, capture_output=True, timeout=180)
        return r.returncode == 0
    except Exception:
        return False
