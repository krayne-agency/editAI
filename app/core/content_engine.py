from __future__ import annotations

from dataclasses import dataclass

try:
    from core.gemini_ai import build_tiktok_content as _gemini_content
    from core.gemini_ai import generate_variants as _gemini_variants
except ImportError:
    _gemini_content = None  # type: ignore[assignment]
    _gemini_variants = None  # type: ignore[assignment]

try:
    from core.brain import get_brain_context as _get_brain_context
except ImportError:
    def _get_brain_context(niche: str = "", tone: str = "") -> dict:  # type: ignore[misc]
        return {}


@dataclass
class ContentVariant:
    hook: str
    title: str


@dataclass
class ContentPackage:
    hook: str
    title: str
    description: str
    hashtags: list[str]
    cta: str


def _clamp(value: int, min_value: int, max_value: int) -> int:
    return max(min_value, min(value, max_value))


def _clean_tags(tags: list[str]) -> list[str]:
    normalized: list[str] = []
    for raw in tags:
        tag = raw.strip().replace(" ", "")
        if not tag:
            continue
        if not tag.startswith("#"):
            tag = f"#{tag}"
        normalized.append(tag.lower())
    return normalized[:8]


def build_content_package(
    profile: dict[str, str],
    video_topic: str,
    goal: str,
    extra_keywords: str,
    api_key: str = "",
    style: str = "standard",
) -> ContentPackage:
    account = profile.get("account_name", "MonCompte")
    niche = profile.get("niche", "création")
    tone = profile.get("tone", "dynamique")
    hook_style = profile.get("hook_style", "direct")
    cta_style = profile.get("cta_style", "commente ton avis")

    topic = video_topic.strip() or niche
    objective = goal.strip() or "engagement"
    keywords = [k.strip() for k in extra_keywords.split(",") if k.strip()]

    # ── Tentative Gemini ──────────────────────────────────────────────────────
    if api_key and api_key.strip() and _gemini_content is not None:
        brain_ctx = _get_brain_context(niche=niche, tone=tone)
        result = _gemini_content(
            niche=niche,
            audience=profile.get("audience", "18-34 ans"),
            tone=tone,
            topic=topic,
            goal=objective,
            language=profile.get("language", "fr"),
            api_key=api_key,
            brain_context=brain_ctx,
            style=style,
        )
        if result:
            return ContentPackage(
                hook=str(result.get("hook", topic)),
                title=str(result.get("title", topic)),
                description=str(result.get("description", "")),
                hashtags=_clean_tags(result.get("hashtags", [])),
                cta=str(result.get("cta", cta_style)),
            )

    # ── Fallback templates locaux ─────────────────────────────────────────────
    hook = f"{topic}: le détail que 90% des gens ratent ({hook_style})"
    title = f"{topic} en 30 secondes - méthode {tone}"

    description = (
        f"Compte: @{account} | Objectif: {objective}. "
        f"Vidéo optimisée pour TikTok vertical 9:16 avec message clair sur {topic}. "
        f"Public cible: {profile.get('audience', '18-34 ans')}."
    )

    base_tags = [
        "tiktokfr",
        "pourtoi",
        "conseils",
        objective,
        niche,
        topic,
    ] + keywords

    hashtags = _clean_tags(base_tags)
    cta = f"{cta_style}. Enregistre cette vidéo pour la revoir plus tard."

    return ContentPackage(
        hook=hook,
        title=title,
        description=description,
        hashtags=hashtags,
        cta=cta,
    )


def package_to_caption(package: ContentPackage) -> str:
    hashtags_text = " ".join(package.hashtags)
    return (
        f"{package.hook}\n\n"
        f"{package.description}\n\n"
        f"{package.cta}\n\n"
        f"{hashtags_text}"
    )


def generate_hook_title_variants(
    profile: dict[str, str],
    video_topic: str,
    goal: str,
    api_key: str = "",
) -> list[ContentVariant]:
    topic = video_topic.strip() or profile.get("niche", "création")
    tone = profile.get("tone", "dynamique")
    objective = goal.strip() or "engagement"

    # ── Tentative Gemini ──────────────────────────────────────────────────────
    if api_key and api_key.strip() and _gemini_variants is not None:
        brain_ctx = _get_brain_context(niche=profile.get("niche", topic), tone=tone)
        raw = _gemini_variants(
            niche=profile.get("niche", topic),
            tone=tone,
            topic=topic,
            goal=objective,
            api_key=api_key,
            brain_context=brain_ctx,
        )
        if raw:
            return [ContentVariant(hook=v["hook"], title=v["title"]) for v in raw]

    # ── Fallback templates locaux ─────────────────────────────────────────────
    return [
        ContentVariant(
            hook=f"Stop: {topic} est mal compris par la majorité",
            title=f"{topic} - version simple et {tone}",
        ),
        ContentVariant(
            hook=f"Tu veux plus de {objective}? Commence par ce point sur {topic}",
            title=f"{topic}: la méthode qui évite 3 erreurs",
        ),
        ContentVariant(
            hook=f"Avant de scroller: voici le levier caché de {topic}",
            title=f"{topic} en 30 sec pour résultats plus rapides",
        ),
    ]


def generate_voiceover_script(
    profile: dict[str, str],
    video_topic: str,
    hook: str,
    goal: str,
    api_key: str = "",
) -> str:
    topic = video_topic.strip() or profile.get("niche", "création")
    tone = profile.get("tone", "dynamique")
    audience = profile.get("audience", "18-34 ans")
    objective = goal.strip() or "engagement"

    lines = [
        f"[0s] {hook.strip()}",
        f"[2s] Voici ce que {audience} ignorent souvent sur {topic}.",
        f"[4s] En {tone}, voici la méthode directe.",
        f"[6s] Retiens bien ça: c'est le levier principal pour {objective}.",
        f"[8s] Commente si tu veux qu'on aille plus loin sur {topic}.",
    ]
    return "\n".join(lines)


def score_content(package: ContentPackage) -> dict[str, int | str]:
    hook_len = len(package.hook)
    title_len = len(package.title)
    hashtags_count = len(package.hashtags)

    hook_score = _clamp(100 - abs(hook_len - 70), 40, 100)
    title_score = _clamp(100 - abs(title_len - 55), 40, 100)
    hashtag_score = _clamp(55 + hashtags_count * 6, 45, 100)

    global_score = int((hook_score * 0.45) + (title_score * 0.35) + (hashtag_score * 0.20))

    if global_score >= 80:
        verdict = "fort potentiel"
    elif global_score >= 65:
        verdict = "bon potentiel"
    else:
        verdict = "à renforcer"

    return {
        "global": global_score,
        "hook": hook_score,
        "title": title_score,
        "hashtags": hashtag_score,
        "verdict": verdict,
    }
