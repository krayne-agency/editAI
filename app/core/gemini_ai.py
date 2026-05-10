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
STYLE: Gaming Viral TikTok 2026 — énergie maximale, chaque seconde compte.
RÈGLES ABSOLUES:
- [0-2s] Hook visuel + texte CHOC en majuscules (ex: "LE GLITCH QUI M'A SAUVÉ 😱", "IMPOSSIBLE MAIS RÉEL 🔥", "LES DEVS VONT ME BANNIR...")
- [2-18s] Gameplay le plus intense : zooms rapides beat-sync, ralentis sur le moment clé, cuts toutes les 1-2s
- [18-28s] CLIMAX : le moment le plus fou, monté avec bass boost + flash blanc + shake cam
- [28-35s] CTA gaming engageant : "Tu notes /10 ? 👀" | "T'aurais survive ?" | "Tag ton squad 🎮"
- Effets obligatoires : shake sur les kills, zoom punch sur les highlight, sous-titres animés énormes (INSANE ! / NO WAY ! / LET'S GO !)
- Musique : phonk / drill / trap beat synced sur les cuts
- Hashtags: #gaming #tiktokgaming #viral #clip #montage #insane #gaming2026 #fyp
- Ton: TOUT EN CAPS sur les mots clés, émojis gaming partout, énergie de streamer qui pop""",
        "educatif": """
STYLE: Éducatif viral — valeur immédiate, rétention maximale.
RÈGLES: Hook question/chiffre choc | 3 points en bullet visuels (texte animé) | "Save si utile" | #apprendreavectiktok #conseil #astuce #tip #viral""",
        "business": """
STYLE: Business / Entrepreneur viral — crédibilité + aspiration.
RÈGLES: Hook résultat concret chiffré | proof social | storytelling 60s | CTA "Commente TON objectif 👇" | #business #entrepreneur #money #success #mindset""",
        "lifestyle": """
STYLE: Lifestyle esthétique viral — FOMO + aspiration pure.
RÈGLES: Hook vibe/émotion sensorielle | plan cinématique | musique tendance | CTA "Save for later ✨" | #lifestyle #aesthetic #vibe #luxe #motivation""",
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
            parts.append(
                f"Ce compte a déjà produit {sessions} vidéos analysées, score moyen {avg_score}/100. "
                f"Génère un contenu qui dépasse ce score en capitalisant sur ce qui a marché."
            )
        if top_kw:
            parts.append(
                f"Mots-clés récurrents PROUVÉS sur ce compte : {', '.join(top_kw[:6])}. "
                f"Intègre-les naturellement dans le hook et les hashtags."
            )
        if good_hooks:
            examples = " | ".join(f'"{h}"' for h in good_hooks[:3])
            parts.append(
                f"Hooks qui ont FONCTIONNÉ sur ce compte : {examples}. "
                f"Utilise la même formule de style mais avec une nouvelle angle d'attaque."
            )
        if good_titles:
            examples = " | ".join(f'"{t}"' for t in good_titles[:3])
            parts.append(
                f"Titres performants : {examples}. "
                f"Respecte le même format (longueur, énergie, structure)."
            )
        if parts:
            brain_section = "\n\nCOMPTE ANALYSÉ — CONTEXTE OBLIGATOIRE:\n" + "\n".join(parts)

    prompt = f"""Tu es un expert TikTok viral de niveau ÉLITE. Tes vidéos font 500K-5M vues.

RÈGLES D'OR DU HOOK VIRAL (obligatoires, non négociables):
1. Le hook doit créer une RUPTURE en < 2s — l'algorithme juge les 2 premières secondes
2. Formules qui cartonnent : 
   - "Personne ne sait que [secret/astuce choc]..."
   - "J'ai failli [perdre/rater/mourir] à cause de ça 😳"
   - "[Chiffre fou] en [temps court] — voici comment"
   - "Le truc que [pros/devs/experts] ne veulent pas que tu voies"
   - "[Action impossible] en [X secondes] — c'est réel"
3. Texte tout en CAPS sur les mots clés, émojis percutants en fin de hook
4. Le hook DOIT créer une tension ou un mystère qui force à regarder la suite

Niche: {niche}
Audience cible: {audience}
Ton: {tone}
Sujet de la vidéo: {topic}
Objectif: {goal}{brain_section}{style_section}

{lang_instruction}
Réponds UNIQUEMENT en JSON valide avec ce format exact:
{{
  "hook": "Hook ULTRA percutant (max 15 mots, formule prouvée virale)",
  "title": "Titre TikTok optimisé SEO (max 60 car, mots-clés en tête)",
  "description": "Description engageante avec question ou CTA (max 120 car)",
  "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5", "#tag6", "#tag7", "#fyp", "#viral"],
  "cta": "CTA qui force l'interaction (like / comment / save / follow — max 10 mots)",
  "voiceover": "Script voix-off CHRONOMÉTRÉ:\\n[0-2s] HOOK choc (phrase d'accroche)\\n[2-10s] Mise en situation / contexte rapide\\n[10-25s] Le moment clé / la valeur / le gameplay\\n[25-30s] Climax / révélation / best moment\\n[30-35s] CTA direct et engageant"
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


def analyze_account(
    niche: str,
    tone: str,
    audience: str,
    language: str,
    brain_context: dict,
    api_key: str,
) -> dict[str, str] | None:
    """
    Analyse le compte et retourne des recommandations stratégiques.
    Retourne {strengths, gaps, next_content, best_time, growth_tip} ou None.
    """
    if not api_key or not api_key.strip():
        return None

    sessions = brain_context.get("sessions_count", 0)
    avg_score = brain_context.get("avg_score", 0.0)
    top_score = brain_context.get("top_score", 0.0)
    top_kw = brain_context.get("top_keywords", [])
    good_hooks = brain_context.get("good_hooks", [])
    good_titles = brain_context.get("good_titles", [])
    learned_niche = brain_context.get("learned_niche", niche)
    learned_tone = brain_context.get("learned_tone", tone)

    lang_instruction = "Réponds UNIQUEMENT en français." if language == "fr" else "Respond ONLY in English."

    data_section = f"""Données du compte:
- Niche: {learned_niche} | Ton: {learned_tone} | Audience: {audience}
- {sessions} vidéos analysées, score moyen {avg_score}/100, meilleur score {top_score}/100
- Mots-clés fréquents: {', '.join(str(k) for k, _ in top_kw[:6]) if top_kw else 'aucun encore'}
- Hooks performants: {' | '.join(f'"{h}"' for h in good_hooks[:2]) if good_hooks else 'aucun encore'}
- Titres performants: {' | '.join(f'"{t}"' for t in good_titles[:2]) if good_titles else 'aucun encore'}"""

    prompt = f"""Tu es un stratège TikTok expert. Analyse ce compte et donne des recommandations précises et actionnables.

{data_section}

{lang_instruction}
Réponds UNIQUEMENT en JSON valide:
{{
  "strengths": "Ce qui fonctionne bien sur ce compte (2-3 points concrets)",
  "gaps": "Ce qui manque ou freine la croissance (2-3 points concrets)",
  "next_content": "Sujet exact de la prochaine vidéo à faire pour maximiser les vues",
  "hook_formula": "La formule de hook qui marche le mieux pour ce compte (1 phrase template)",
  "growth_tip": "Le conseil le plus important pour doubler les vues sur les prochaines vidéos"
}}"""

    raw = _call(prompt, api_key, max_tokens=600)
    if not raw:
        return None
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group())
        if {"strengths", "gaps", "next_content", "hook_formula", "growth_tip"}.issubset(data.keys()):
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

    prompt = f"""Tu es un expert TikTok viral ÉLITE. Génère 3 variantes de hooks ULTRA percutants pour:

Niche: {niche}
Ton: {tone}
Sujet: {topic}
Objectif: {goal}{brain_section}

Utilise ces 3 formules virales PROUVÉES:
- Variante 1 (CHOC/PEUR): "J'ai failli [désastre] à cause de [élément du sujet]..." | "Ce [truc] peut [conséquence choc]..."
- Variante 2 (SECRET/INTERDIT): "Le secret que [pros/devs/experts] cachent sur [sujet]" | "Personne ne parle de ça..."  
- Variante 3 (DÉFI/IMPOSSIBLE): "[Action] en [temps court] — 99% échouent" | "Seuls les [top X%] connaissent ça"

RÈGLE: chaque hook max 12 mots, mots clés en CAPS, 1-2 émojis percutants.

Réponds UNIQUEMENT en JSON valide:
[
  {{"hook": "...", "title": "Titre SEO optimisé variante 1"}},
  {{"hook": "...", "title": "Titre SEO optimisé variante 2"}},
  {{"hook": "...", "title": "Titre SEO optimisé variante 3"}}
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
