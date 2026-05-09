"""
gemini_ai.py — Intégration Gemini 2.0 Flash pour editAI.
Fallback automatique sur templates locaux si pas de clé ou pas d'internet.
Aucune dépendance externe : urllib seulement.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Any

_GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent"
)
_TIMEOUT = 12


# ── Réseau ────────────────────────────────────────────────────────────────────

def _post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8"))


def _call(prompt: str, api_key: str, max_tokens: int = 600) -> str:
    """Appel bas niveau. Retourne '' si erreur ou clé vide."""
    if not api_key or not api_key.strip():
        return ""
    try:
        url = f"{_GEMINI_URL}?key={api_key.strip()}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.85},
        }
        response = _post_json(url, payload)
        candidates = response.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                return str(parts[0].get("text", "")).strip()
    except Exception:  # noqa: BLE001
        pass
    return ""


# ── API publique ──────────────────────────────────────────────────────────────

def test_key(api_key: str) -> tuple[bool, str]:
    """Teste la validité d'une clé. Retourne (valide, message_court)."""
    if not api_key or not api_key.strip():
        return False, "Clé vide"
    try:
        url = f"{_GEMINI_URL}?key={api_key.strip()}"
        payload = {
            "contents": [{"parts": [{"text": "OK"}]}],
            "generationConfig": {"maxOutputTokens": 4},
        }
        _post_json(url, payload)
        return True, "Connecté ✓"
    except urllib.error.HTTPError as e:
        if e.code == 429:
            return True, "Quota (clé valide) ✓"
        if e.code in (400, 403):
            return False, f"Clé invalide ({e.code})"
        return False, f"Erreur HTTP {e.code}"
    except Exception as ex:  # noqa: BLE001
        return False, f"Réseau : {ex}"


def build_tiktok_content(
    niche: str,
    audience: str,
    tone: str,
    topic: str,
    goal: str,
    language: str,
    api_key: str,
    brain_context: dict | None = None,
    style: str = "standard",
) -> dict[str, Any] | None:
    """
    Génère un package complet TikTok via Gemini.
    Retourne un dict {hook, title, description, hashtags, cta, voiceover} ou None si échec.
    brain_context : dict retourné par brain.get_brain_context() pour enrichir le prompt.
    style : "standard" | "gaming_viral" | "educatif" | "business" | "lifestyle"
    """
    lang_instruction = "Réponds UNIQUEMENT en français." if language == "fr" else "Respond ONLY in English."

    # ── Style-specific instructions ───────────────────────────────────────────
    _style_instructions = {
        "gaming_viral": """
STYLE: Gaming Viral TikTok 2026 — ultra addictif, montage rapide, énergie maximale.
Rules OBLIGATOIRES:
- Hook dans les 3 premières secondes : texte énorme et percutant (ex: "Le move le plus INSANE que tu verras aujourd'hui 😳" / "Personne ne réussit ça...")
- Script chronometre: [0-3s] hook | [3-20s] gameplay intense (zooms, ralentis, cuts beat-sync) | [20-28s] climax choquant + bass boost + flash | [28-35s] CTA engageant
- Effets visuels: glow, shake, motion blur, sous-titres animés énormes, emojis gaming
- Ambiance e-sport/streamer : couleurs néon/RGB, vibe cyberpunk
- CTA gaming obligatoire : "Tu notes ce clip /10 ? 👀" ou "Tu aurais réussi ?"
- Hashtags UNIQUEMENT gaming : #gaming #tiktokgaming #viral #clip #gaming2026 #insane #montage
- Ton : excitation maximale, all-caps sur les mots clés, énergique""",
        "educatif": """
STYLE: Éducatif viral TikTok — valeur immédiate, pédagogie dynamique.
Rules: hook question/chiffre choc | contenu en bullet points visuels | CTA "Enregistre si utile" | hashtags #apprendreavectiktok #conseil #astuce""",
        "business": """
STYLE: Business / Entrepreneur viral — crédibilité + aspiration.
Rules: hook résultat concret (ex: "J'ai gagné 10k ce mois") | proof social | CTA "Commente TON objectif" | hashtags #business #entrepreneur #money #success""",
        "lifestyle": """
STYLE: Lifestyle esthétique viral — aspiration, FOMO, atmosphère.
Rules: hook vibe/émotion | esthétique cinématique | CTA "Save for later" | hashtags #lifestyle #aesthetic #vibe #luxe""",
        "standard": "",
    }
    style_section = _style_instructions.get(style, "")

    # ── Injection du contexte appris (few-shot examples) ─────────────────────
    brain_section = ""
    if brain_context:
        good_hooks = brain_context.get("good_hooks", [])
        good_titles = brain_context.get("good_titles", [])
        top_kw = brain_context.get("top_keywords", [])
        sessions = brain_context.get("sessions_count", 0)
        avg_score = brain_context.get("avg_score", 0.0)

        parts: list[str] = []
        if sessions > 0:
            parts.append(f"Contexte utilisateur: {sessions} vidéos analysées, score moyen {avg_score}/100.")
        if top_kw:
            parts.append(f"Mots-clés récurrents de ce compte: {', '.join(top_kw[:6])}.")
        if good_hooks:
            examples = " | ".join(f'"{h}"' for h in good_hooks[:3])
            parts.append(f"Hooks validés performants (inspire-toi du style, ne copie pas): {examples}.")
        if good_titles:
            examples = " | ".join(f'"{t}"' for t in good_titles[:3])
            parts.append(f"Titres validés performants: {examples}.")
        if parts:
            brain_section = "\n\nCONTEXTE APPRIS:\n" + "\n".join(parts)

    prompt = f"""Tu es un expert TikTok viral. Génère un package complet pour une vidéo courte.

Niche: {niche}
Audience cible: {audience}
Ton: {tone}
Sujet de la vidéo: {topic}
Objectif: {goal}{brain_section}{style_section}

{lang_instruction}
Réponds UNIQUEMENT en JSON valide avec ce format exact:
{{
  "hook": "Phrase d'accroche ultra-percutante (max 15 mots) pour les 2 premières secondes",
  "title": "Titre TikTok optimisé (max 60 caractères)",
  "description": "Description mobile-first engageante (max 120 caractères)",
  "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5", "#tag6", "#tag7"],
  "cta": "Call-to-action court et direct (max 10 mots)",
  "voiceover": "Script voix-off chronométré:\\n[0s] hook percutant\\n[2s] développement\\n[4s] valeur ajoutée\\n[6s] solution\\n[8s] CTA"
}}"""

    raw = _call(prompt, api_key, max_tokens=700)
    if not raw:
        return None

    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return None

    try:
        data = json.loads(match.group())
        required = {"hook", "title", "description", "hashtags", "cta", "voiceover"}
        if required.issubset(data.keys()):
            return data
    except (json.JSONDecodeError, KeyError):
        pass
    return None


def generate_variants(
    niche: str,
    tone: str,
    topic: str,
    goal: str,
    api_key: str,
    brain_context: dict | None = None,
) -> list[dict[str, str]] | None:
    """
    Génère 3 variantes hook+titre. Retourne liste de {hook, title} ou None.
    brain_context : optionnel, pour enrichir le prompt avec les exemples appris.
    """
    brain_section = ""
    if brain_context:
        good_hooks = brain_context.get("good_hooks", [])
        if good_hooks:
            examples = " | ".join(f'"{h}"' for h in good_hooks[:3])
            brain_section = f"\n\nCONTEXTE: Hooks validés comme performants sur ce compte (inspire le style, varie les formules): {examples}."

    prompt = f"""Tu es un expert TikTok. Génère 3 variantes DIFFÉRENTES de hook+titre pour:

Niche: {niche}
Ton: {tone}
Sujet: {topic}
Objectif: {goal}{brain_section}

Utilise 3 formules différentes:
- Variante 1: Question provocatrice
- Variante 2: Chiffre ou statistique choc
- Variante 3: Révélation ou secret

Réponds UNIQUEMENT en JSON valide:
[
  {{"hook": "...", "title": "..."}},
  {{"hook": "...", "title": "..."}},
  {{"hook": "...", "title": "..."}}
]"""

    raw = _call(prompt, api_key, max_tokens=400)
    if not raw:
        return None

    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if not match:
        return None

    try:
        data = json.loads(match.group())
        result = [
            {"hook": str(item.get("hook", "")), "title": str(item.get("title", ""))}
            for item in data
            if isinstance(item, dict) and item.get("hook") and item.get("title")
        ]
        return result[:3] if result else None
    except (json.JSONDecodeError, KeyError):
        return None
