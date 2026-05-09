from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass
class ProfileInsights:
    account_name: str
    niche: str
    audience: str
    tone: str
    language: str
    post_frequency: str
    best_posting_window: str
    hook_style: str
    cta_style: str


def _safe_mode(series: pd.Series, fallback: str) -> str:
    if series.empty:
        return fallback
    mode_values = series.mode(dropna=True)
    if mode_values.empty:
        return fallback
    value = str(mode_values.iloc[0]).strip()
    return value if value else fallback


def _column_lookup(df: pd.DataFrame) -> dict[str, str]:
    return {c.lower().strip(): c for c in df.columns}


def _pick_mode_from_candidates(
    df: pd.DataFrame,
    columns: dict[str, str],
    candidates: list[str],
    fallback: str,
) -> str:
    for candidate in candidates:
        real_col = columns.get(candidate)
        if real_col:
            return _safe_mode(df[real_col], fallback)
    return fallback


def analyze_profile(
    account_name: str,
    niche: str,
    audience: str,
    tone: str,
    language: str,
    post_frequency: str,
    csv_df: pd.DataFrame | None = None,
) -> ProfileInsights:
    best_window = "18:00-21:00"
    hook_style = "direct et concret"
    cta_style = "commente ton avis"

    if csv_df is not None and not csv_df.empty:
        columns = _column_lookup(csv_df)
        best_window = _pick_mode_from_candidates(
            csv_df, columns, ["hour", "heure"], best_window
        )
        hook_style = _pick_mode_from_candidates(
            csv_df, columns, ["hook_type", "hook"], hook_style
        )
        cta_style = _pick_mode_from_candidates(
            csv_df, columns, ["cta"], cta_style
        )

    return ProfileInsights(
        account_name=account_name.strip() or "MonCompte",
        niche=niche.strip() or "Création de contenu",
        audience=audience.strip() or "18-34 ans",
        tone=tone.strip() or "dynamique",
        language=language.strip() or "fr",
        post_frequency=post_frequency.strip() or "1 vidéo/jour",
        best_posting_window=best_window,
        hook_style=hook_style,
        cta_style=cta_style,
    )


def insights_to_dict(insights: ProfileInsights) -> dict[str, Any]:
    return {
        "account_name": insights.account_name,
        "niche": insights.niche,
        "audience": insights.audience,
        "tone": insights.tone,
        "language": insights.language,
        "post_frequency": insights.post_frequency,
        "best_posting_window": insights.best_posting_window,
        "hook_style": insights.hook_style,
        "cta_style": insights.cta_style,
    }
