"""
brain.py — Cerveau IA d'EditAI.

Mémorise chaque session d'analyse, apprend les préférences de l'utilisateur,
et enrichit les prompts Gemini avec les exemples qui ont bien fonctionné.
Stockage : workspace_data/brain/ (JSON local, pas de cloud, pas de dépendance).
"""
from __future__ import annotations

import json
import time
from pathlib import Path

_BRAIN_DIR = Path(__file__).resolve().parents[2] / "workspace_data" / "brain"
_PROFILE_FILE = _BRAIN_DIR / "profile.json"
_HISTORY_FILE = _BRAIN_DIR / "history.json"


def _ensure_dirs() -> None:
    _BRAIN_DIR.mkdir(parents=True, exist_ok=True)


# ── Profil appris ─────────────────────────────────────────────────────────────

def load_profile() -> dict:
    """Charge le profil appris. Retourne un dict vide si premier lancement."""
    _ensure_dirs()
    if _PROFILE_FILE.exists():
        try:
            return json.loads(_PROFILE_FILE.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            pass
    return {
        "niche": "",
        "tone": "",
        "audience": "",
        "language": "fr",
        "keywords_freq": {},   # keyword → nombre d'utilisations
        "good_hooks": [],      # hooks marqués ⭐ par l'utilisateur (max 20)
        "good_titles": [],     # titres marqués ⭐ (max 20)
        "good_hashtags": [],   # lots de hashtags marqués ⭐ (max 10)
        "sessions_count": 0,
        "avg_score": 0.0,
        "top_score": 0.0,
        "last_updated": "",
    }


def save_profile(profile: dict) -> None:
    _ensure_dirs()
    profile["last_updated"] = time.strftime("%Y-%m-%d %H:%M")
    _PROFILE_FILE.write_text(
        json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ── Historique sessions ───────────────────────────────────────────────────────

def load_history() -> list[dict]:
    _ensure_dirs()
    if _HISTORY_FILE.exists():
        try:
            return json.loads(_HISTORY_FILE.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            pass
    return []


def save_session(session: dict) -> None:
    """
    Sauvegarde une session et met à jour le profil appris.

    session doit contenir : hook, title, hashtags (list), keywords (list),
    score (int), niche, tone, audience, language
    """
    _ensure_dirs()
    session = dict(session)
    session["timestamp"] = time.strftime("%Y-%m-%d %H:%M")

    history = load_history()
    history.insert(0, session)
    history = history[:100]  # garder les 100 dernières
    _HISTORY_FILE.write_text(
        json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # ── Mettre à jour le profil ───────────────────────────────────────────────
    profile = load_profile()

    # Mémoriser niche / tone / audience si remplis
    for field in ("niche", "tone", "audience", "language"):
        val = session.get(field, "")
        if val:
            profile[field] = val

    # Fréquence des mots-clés
    for kw in session.get("keywords", []):
        kw = kw.strip().lower()
        if kw:
            profile["keywords_freq"][kw] = profile["keywords_freq"].get(kw, 0) + 1

    # Score moyen et top
    score = float(session.get("score", 0))
    n = len(history)
    profile["sessions_count"] = n
    if score > 0:
        old_avg = float(profile.get("avg_score", 0.0))
        profile["avg_score"] = round((old_avg * (n - 1) + score) / n, 1)
        if score > float(profile.get("top_score", 0.0)):
            profile["top_score"] = score

    # ── Auto-apprentissage : mémoriser automatiquement si score >= 72 ──────────
    if score >= 72:
        hook = session.get("hook", "").strip()
        if hook and hook not in profile.get("good_hooks", []):
            lst = profile.get("good_hooks", [])
            lst.insert(0, hook)
            profile["good_hooks"] = lst[:20]
        title = session.get("title", "").strip()
        if title and title not in profile.get("good_titles", []):
            lst = profile.get("good_titles", [])
            lst.insert(0, title)
            profile["good_titles"] = lst[:20]
        hashtags = session.get("hashtags", [])
        if isinstance(hashtags, list) and hashtags:
            ht_str = " ".join(str(h) for h in hashtags if h)
            if ht_str and ht_str not in profile.get("good_hashtags", []):
                lst = profile.get("good_hashtags", [])
                lst.insert(0, ht_str)
                profile["good_hashtags"] = lst[:10]

    save_profile(profile)


# ── Feedback utilisateur ──────────────────────────────────────────────────────

def mark_good(content_type: str, content: str) -> None:
    """
    Marque un contenu comme bon pour l'injecter dans les prochains prompts.
    content_type : "hook" | "title" | "hashtags"
    """
    if not content or not content.strip():
        return
    profile = load_profile()
    key = f"good_{content_type}s"          # good_hooks / good_titles / good_hashtags
    lst: list[str] = profile.get(key, [])
    if content not in lst:
        lst.insert(0, content)
        limit = 10 if content_type == "hashtags" else 20
        lst = lst[:limit]
        profile[key] = lst
        save_profile(profile)


# ── Contexte pour prompts ─────────────────────────────────────────────────────

def get_brain_context(niche: str = "", tone: str = "") -> dict:
    """
    Retourne le contexte appris à injecter dans les prompts Gemini.
    Inclut les hooks/titres performants comme exemples few-shot.
    """
    profile = load_profile()

    # Top mots-clés (10 les plus fréquents)
    freq: dict[str, int] = profile.get("keywords_freq", {})
    top_kw = [k for k, _ in sorted(freq.items(), key=lambda x: x[1], reverse=True)[:10]]

    return {
        "sessions_count": profile.get("sessions_count", 0),
        "avg_score": profile.get("avg_score", 0.0),
        "top_score": profile.get("top_score", 0.0),
        "top_keywords": top_kw,
        "good_hooks": profile.get("good_hooks", [])[:5],
        "good_titles": profile.get("good_titles", [])[:5],
        "good_hashtags": profile.get("good_hashtags", [])[:3],
        "learned_niche": profile.get("niche", niche),
        "learned_tone": profile.get("tone", tone),
        "learned_audience": profile.get("audience", ""),
    }


# ── Stats UI ──────────────────────────────────────────────────────────────────

def get_stats() -> dict:
    """Stats destinées à l'affichage dans l'interface."""
    profile = load_profile()
    history = load_history()

    top_kw = sorted(
        profile.get("keywords_freq", {}).items(),
        key=lambda x: x[1],
        reverse=True,
    )[:8]

    return {
        "sessions": profile.get("sessions_count", 0),
        "avg_score": profile.get("avg_score", 0.0),
        "top_score": profile.get("top_score", 0.0),
        "good_hooks_count": len(profile.get("good_hooks", [])),
        "good_titles_count": len(profile.get("good_titles", [])),
        "top_keywords": top_kw,
        "recent": history[:5],
        "learned_niche": profile.get("niche", ""),
        "learned_tone": profile.get("tone", ""),
    }
