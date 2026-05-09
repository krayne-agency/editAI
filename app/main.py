from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from core.content_engine import (
    build_content_package,
    generate_hook_title_variants,
    generate_voiceover_script,
    package_to_caption,
    score_content,
)
from core.exporter import write_publish_package
from core.gemini_ai import test_key as test_gemini_key
from core.opening_analyzer import analysis_to_dict, analyze_opening
from core.profile_analyzer import analyze_profile, insights_to_dict
from core.video_engine import (
    VideoProcessingError,
    prepare_tiktok_video,
    resolve_ffmpeg_binary,
    resolve_ffprobe_binary,
)
try:
    from core import brain as _brain
except ImportError:
    _brain = None  # type: ignore[assignment]

try:
    from core.overlay_engine import add_hook_overlay, add_subtitles_overlay
    from core.music_engine import get_music_library, mix_music, select_music
    _overlay_ok = True
except ImportError:
    _overlay_ok = False
    def add_hook_overlay(*a, **k) -> bool: return False  # type: ignore[misc]
    def add_subtitles_overlay(*a, **k) -> bool: return False  # type: ignore[misc]
    def get_music_library() -> list: return []  # type: ignore[misc]
    def mix_music(*a, **k) -> bool: return False  # type: ignore[misc]
    def select_music(*a, **k): return None  # type: ignore[misc]

ROOT = Path(__file__).resolve().parents[1]
UPLOADS_DIR = ROOT / "workspace_data" / "uploads"
EXPORTS_DIR = ROOT / "workspace_data" / "exports"
_GEMINI_KEY_FILE = ROOT / "workspace_data" / ".gemini_key"
_ASSETS_DIR = Path(__file__).resolve().parent / "assets"

_CSS = """
<style>
/* ── Base ─────────────────────────────────────────────────────────────── */
html, body, [data-testid="stAppViewContainer"],
[data-testid="stApp"] {
    background: #0a0f1a !important;
    color: #e2e8f0 !important;
}
[data-testid="stSidebar"] {
    background: #0d1424 !important;
    border-right: 1px solid #1e2d45 !important;
}
/* Header */
[data-testid="stHeader"] { background: transparent !important; }

/* ── Cacher éléments Streamlit inutiles ───────────────────────────────── */
[data-testid="stToolbar"],
[data-testid="stDecoration"],
#MainMenu,
.stDeployButton,
button[title="Deploy"],
[data-testid="stMainMenuPopover"] { display: none !important; }

/* ── Bouton réouverture sidebar ────────────────────────────────────────── */
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"],
button[aria-label="Open sidebar"],
button[title="Open sidebar"] {
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    z-index: 999999 !important;
    background: #0d1424 !important;
    border: 1px solid #1e3a5f !important;
    border-radius: 0 8px 8px 0 !important;
    color: #83FFC7 !important;
    min-width: 28px !important;
    min-height: 48px !important;
}
[data-testid="collapsedControl"]:hover,
[data-testid="stSidebarCollapsedControl"]:hover {
    background: #1e3a5f !important;
}
/* Forcer le header visible pour que le toggle ne passe pas derrière */
[data-testid="stHeader"] {
    z-index: 99 !important;
    pointer-events: auto !important;
}

/* ── Titres ───────────────────────────────────────────────────────────── */
h1, h2, h3, h4, p, label, span, div { color: #e2e8f0; }
.editai-brand {
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 8px 0 18px 0;
    border-bottom: 1px solid #1e3a5f;
    margin-bottom: 20px;
}
.editai-brand-name {
    font-size: 2rem;
    font-weight: 800;
    letter-spacing: -1px;
    background: linear-gradient(135deg, #83FFC7 0%, #38bdf8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    line-height: 1;
}
.editai-brand-sub {
    font-size: 0.78rem;
    color: #64748b;
    margin-top: 3px;
    letter-spacing: 0.5px;
}
/* ── Sidebar brand ────────────────────────────────────────────────────── */
.sidebar-logo {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px 0 16px 0;
    border-bottom: 1px solid #1e2d45;
    margin-bottom: 16px;
}
.sidebar-logo-name {
    font-size: 1.25rem;
    font-weight: 800;
    background: linear-gradient(135deg, #83FFC7 0%, #38bdf8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

/* ── Boutons Streamlit ────────────────────────────────────────────────── */
[data-testid="stButton"] > button {
    background: linear-gradient(135deg, #0f766e, #0e7490) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    transition: opacity 0.15s;
}
[data-testid="stButton"] > button:hover { opacity: 0.85 !important; }
[data-testid="stButton"] > button[kind="primary"] {
    background: linear-gradient(135deg, #0f766e, #0369a1) !important;
    font-size: 1rem !important;
    padding: 12px !important;
}

/* ── Inputs ───────────────────────────────────────────────────────────── */
[data-testid="stTextInput"] input,
textarea {
    background: #111827 !important;
    border-color: #1e3a5f !important;
    color: #e2e8f0 !important;
}
/* Selectbox */
[data-baseweb="select"] > div,
[data-baseweb="select"] [data-testid="stSelectbox"] {
    background: #111827 !important;
    border-color: #1e3a5f !important;
    color: #e2e8f0 !important;
}
[data-baseweb="popover"] [role="option"],
[data-baseweb="menu"] { background: #111827 !important; color: #e2e8f0 !important; }
[data-baseweb="menu"] [role="option"]:hover { background: #1e3a5f !important; }

/* Checkbox */
[data-testid="stCheckbox"] label { color: #e2e8f0 !important; }

/* ── Metrics ──────────────────────────────────────────────────────────── */
[data-testid="metric-container"] {
    background: #111827 !important;
    border: 1px solid #1e3a5f !important;
    border-radius: 12px !important;
    padding: 14px !important;
}
[data-testid="stMetricValue"] { color: #83FFC7 !important; font-weight: 700 !important; }
[data-testid="stMetricLabel"] { color: #94a3b8 !important; }
[data-testid="stMetricDelta"] { color: #38bdf8 !important; }

/* ── Divider ──────────────────────────────────────────────────────────── */
hr { border-color: #1e2d45 !important; }

/* ── Upload zone ──────────────────────────────────────────────────────── */
[data-testid="stFileUploader"] {
    background: #111827 !important;
    border: 2px dashed #1e3a5f !important;
    border-radius: 12px !important;
}
[data-testid="stFileUploader"] label,
[data-testid="stFileUploader"] span { color: #94a3b8 !important; }

/* ── Captions & markdown ─────────────────────────────────────────────── */
[data-testid="stCaptionContainer"],
.stMarkdown p, .stMarkdown span { color: #94a3b8 !important; }

/* ── Alerts ───────────────────────────────────────────────────────────── */
[data-testid="stAlert"] { background: #111827 !important; border-color: #1e3a5f !important; }

/* ── Scrollbar ────────────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #0a0f1a; }
::-webkit-scrollbar-thumb { background: #1e3a5f; border-radius: 3px; }
</style>
"""

_LOGO_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="52" height="52">
  <defs>
    <linearGradient id="bg2" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#0f766e"/><stop offset="100%" style="stop-color:#083344"/>
    </linearGradient>
    <linearGradient id="sp2" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#83FFC7"/><stop offset="100%" style="stop-color:#38bdf8"/>
    </linearGradient>
  </defs>
  <rect width="200" height="200" rx="40" ry="40" fill="url(#bg2)"/>
  <rect x="38" y="52" width="52" height="12" rx="6" fill="url(#sp2)"/>
  <rect x="38" y="94" width="42" height="12" rx="6" fill="url(#sp2)"/>
  <rect x="38" y="136" width="52" height="12" rx="6" fill="url(#sp2)"/>
  <rect x="38" y="52" width="12" height="96" rx="6" fill="url(#sp2)"/>
  <polygon points="118,48 100,108 116,108 98,158 144,90 124,90 142,48" fill="url(#sp2)" opacity="0.95"/>
</svg>"""

_LOGO_SMALL_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="32" height="32">
  <defs>
    <linearGradient id="bg3" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#0f766e"/><stop offset="100%" style="stop-color:#083344"/>
    </linearGradient>
    <linearGradient id="sp3" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#83FFC7"/><stop offset="100%" style="stop-color:#38bdf8"/>
    </linearGradient>
  </defs>
  <rect width="200" height="200" rx="40" ry="40" fill="url(#bg3)"/>
  <rect x="38" y="52" width="52" height="12" rx="6" fill="url(#sp3)"/>
  <rect x="38" y="94" width="42" height="12" rx="6" fill="url(#sp3)"/>
  <rect x="38" y="136" width="52" height="12" rx="6" fill="url(#sp3)"/>
  <rect x="38" y="52" width="12" height="96" rx="6" fill="url(#sp3)"/>
  <polygon points="118,48 100,108 116,108 98,158 144,90 124,90 142,48" fill="url(#sp3)" opacity="0.95"/>
</svg>"""


def _load_gemini_key() -> str:
    try:
        return _GEMINI_KEY_FILE.read_text(encoding="utf-8").strip()
    except (FileNotFoundError, OSError):
        return ""


def _save_gemini_key(key: str) -> None:
    _GEMINI_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    _GEMINI_KEY_FILE.write_text(key.strip(), encoding="utf-8")


def save_upload(uploaded_file) -> Path:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    target = UPLOADS_DIR / uploaded_file.name
    with open(target, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return target


def read_optional_csv(uploaded_csv) -> pd.DataFrame | None:
    if uploaded_csv is None:
        return None
    try:
        return pd.read_csv(uploaded_csv)
    except Exception:
        return None


def copy_button(text_to_copy: str, label: str, key: str) -> None:
        escaped = (
                text_to_copy.replace("\\", "\\\\")
                .replace("`", "\\`")
                .replace("${", "\\${")
        )
        html = f"""
        <button id="{key}" style="
                width: 100%;
                background: #0f766e;
                color: #ffffff;
                border: 0;
                border-radius: 8px;
                padding: 8px 10px;
                font-weight: 600;
                cursor: pointer;">
                {label}
        </button>
        <script>
        const btn = document.getElementById('{key}');
        if (btn) {{
            btn.onclick = async () => {{
                try {{
                    await navigator.clipboard.writeText(`{escaped}`);
                    btn.innerText = 'Copié';
                    setTimeout(() => btn.innerText = '{label}', 1200);
                }} catch (e) {{
                    btn.innerText = 'Copie impossible';
                    setTimeout(() => btn.innerText = '{label}', 1500);
                }}
            }};
        }}
        </script>
        """
        components.html(html, height=44)


def main() -> None:
    st.set_page_config(
        page_title="EditAI — TikTok Ready",
        page_icon="⚡",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # CSS global + logo inline
    st.markdown(_CSS, unsafe_allow_html=True)

    # ── Header principal ──────────────────────────────────────────────────
    st.markdown(
        f"""<div class="editai-brand">
            {_LOGO_SVG}
            <div>
                <div class="editai-brand-name">EditAI</div>
                <div class="editai-brand-sub">Préparation vidéo TikTok · Powered by Gemini</div>
            </div>
        </div>""",
        unsafe_allow_html=True,
    )

    with st.sidebar:
        # Logo sidebar
        st.markdown(
            f"""<div class="sidebar-logo">
                {_LOGO_SMALL_SVG}
                <div class="sidebar-logo-name">EditAI</div>
            </div>""",
            unsafe_allow_html=True,
        )
        st.markdown("**Profil compte**")
        account_name = st.text_input("Nom du compte", value="MonCompte")
        niche = st.text_input("Niche", value="Marketing digital")
        audience = st.text_input("Audience", value="18-34 ans")
        tone = st.selectbox("Ton", ["dynamique", "expert", "amical", "premium"])
        language = st.selectbox("Langue", ["fr", "en"])
        post_frequency = st.text_input("Fréquence", value="1 vidéo/jour")
        perf_csv = st.file_uploader("CSV performances (optionnel)", type=["csv"])

        st.divider()
        st.markdown("**🤖 Gemini AI** *(optionnel)*")
        st.caption("Clé gratuite sur [aistudio.google.com](https://aistudio.google.com/app/apikey)")
        saved_key = _load_gemini_key()
        gemini_key = st.text_input(
            "Clé API Gemini",
            value=saved_key,
            type="password",
            placeholder="AIza...",
            key="gemini_key_input",
        )
        col_test, col_save = st.columns(2)
        with col_test:
            if st.button("Tester", key="btn_test_gemini"):
                if gemini_key.strip():
                    with st.spinner("Test..."):
                        ok, msg = test_gemini_key(gemini_key)
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)
                else:
                    st.warning("Clé vide")
        with col_save:
            if st.button("Sauver", key="btn_save_gemini"):
                _save_gemini_key(gemini_key)
                st.success("Sauvegardée")
        if gemini_key.strip():
            st.caption("✅ IA Gemini active — contenu généré par IA")
        else:
            st.caption("○ Mode templates locaux")

        # ── Mémoire IA ───────────────────────────────────────────────────
        st.divider()
        if _brain is not None:
            stats = _brain.get_stats()
            with st.expander(f"🧠 Mémoire IA — {stats['sessions']} sessions", expanded=False):
                if stats["sessions"] == 0:
                    st.caption("Aucune session encore. Lance une première analyse !")
                else:
                    brain_c1, brain_c2 = st.columns(2)
                    brain_c1.metric("Score moyen", f"{stats['avg_score']}/100")
                    brain_c2.metric("Meilleur score", f"{stats['top_score']}/100")
                    st.caption(f"⭐ {stats['good_hooks_count']} hooks validés — {stats['good_titles_count']} titres validés")
                    if stats["learned_niche"]:
                        st.caption(f"Niche apprise: **{stats['learned_niche']}** · Ton: **{stats['learned_tone']}**")
                    if stats["top_keywords"]:
                        kw_str = " · ".join(f"{k} ({v}x)" for k, v in stats["top_keywords"][:5])
                        st.caption(f"Mots-clés fréquents: {kw_str}")
                    if stats["recent"]:
                        st.caption("Sessions récentes:")
                        for s in stats["recent"][:3]:
                            ts = s.get("timestamp", "")
                            sc = s.get("score", "?")
                            topic_s = s.get("topic", "")[:30]
                            st.caption(f"  • {ts} — {topic_s} (score: {sc})")

    col1, col2 = st.columns([1.2, 1])

    with col1:
        st.subheader("1) Vidéo")
        uploaded_video = st.file_uploader("Choisis la vidéo source", type=["mp4", "mov", "mkv", "avi"])
        video_topic = st.text_input("Sujet de la vidéo", value="Astuce croissance TikTok")
        goal = st.selectbox("Objectif", ["engagement", "vues", "conversion", "abonnés"])
        extra_keywords = st.text_input("Mots-clés (séparés par virgules)", value="viral,conseil,2026")
        opening_mode = st.checkbox("Mode analyse ouverture (3 premières secondes)", value=True)

        st.markdown("---")
        st.markdown("**🎬 Améliorations vidéo**")
        add_hook_anim = st.checkbox("Animer le hook sur la vidéo", value=False, key="cb_hook_anim")
        add_subs = st.checkbox("Ajouter sous-titres automatiques", value=False, key="cb_subs")
        add_music_opt = st.checkbox("Musique de fond", value=False, key="cb_music")

        music_volume = -20.0
        music_file_path: str | None = None
        if add_music_opt:
            library = get_music_library()
            if library:
                choices = {f.name: str(f) for f in library}
                chosen = st.selectbox("Piste musicale", list(choices.keys()), key="music_select")
                music_file_path = choices[chosen]
                music_volume = float(st.slider("Volume musique (dB)", -35, -5, -20, key="music_vol",
                                               help="-30 = très discret · -20 = fond · -10 = présent"))
            else:
                workspace_music = str(ROOT / "workspace_data" / "music")
                st.info(f"🎵 Dépose des fichiers .mp3 / .wav dans :\n`{workspace_music}`")
                add_music_opt = False

        run = st.button("Analyser et préparer", type="primary", use_container_width=True)

    with col2:
        st.subheader("2) Résultats")
        st.caption("Après traitement: vidéo à gauche, texte TikTok à droite, hashtags en dessous.")

    if not run and "editai_results" not in st.session_state:
        return

    # ── Traitement (seulement si bouton cliqué) ───────────────────────────────
    if run:
        if uploaded_video is None:
            st.error("Ajoute une vidéo avant de lancer le traitement.")
            return

        csv_df = read_optional_csv(perf_csv)
        profile = analyze_profile(
            account_name=account_name,
            niche=niche,
            audience=audience,
            tone=tone,
            language=language,
            post_frequency=post_frequency,
            csv_df=csv_df,
        )
        profile_dict = insights_to_dict(profile)

        try:
            source_path = save_upload(uploaded_video)
            opening_analysis_dict = None
            if opening_mode:
                ffmpeg_bin = resolve_ffmpeg_binary()
                ffprobe_bin = resolve_ffprobe_binary()
                if ffmpeg_bin and ffprobe_bin:
                    opening_analysis = analyze_opening(source_path, ffmpeg_bin, ffprobe_bin)
                    opening_analysis_dict = analysis_to_dict(opening_analysis)

            media = prepare_tiktok_video(
                source_path,
                EXPORTS_DIR,
                opening_analysis=opening_analysis_dict,
            )
        except VideoProcessingError as exc:
            st.error(str(exc))
            return
        except RuntimeError as exc:
            st.warning(f"Analyse ouverture non disponible: {exc}")
            media = prepare_tiktok_video(source_path, EXPORTS_DIR, opening_analysis=None)
            opening_analysis_dict = None

        content_package = build_content_package(
            profile=profile_dict,
            video_topic=video_topic,
            goal=goal,
            extra_keywords=extra_keywords,
            api_key=gemini_key,
        )
        caption = package_to_caption(content_package)
        variants = generate_hook_title_variants(profile_dict, video_topic, goal, api_key=gemini_key)
        content_score = score_content(content_package)
        voiceover = generate_voiceover_script(
            profile=profile_dict,
            video_topic=video_topic,
            hook=content_package.hook,
            goal=goal,
            api_key=gemini_key,
        )

        content_dict = {
            "hook": content_package.hook,
            "title": content_package.title,
            "description": content_package.description,
            "hashtags": content_package.hashtags,
            "cta": content_package.cta,
            "caption": caption,
        }

        # ── Overlays animés + musique ─────────────────────────────────────────
        enhanced_video = media["processed_video"]
        if add_hook_anim or add_subs or add_music_opt:
            _ffmpeg = resolve_ffmpeg_binary()
            if _ffmpeg:
                _cur = enhanced_video
                _exp = Path(enhanced_video).parent

                if add_hook_anim:
                    _out = str(_exp / f"hook_{Path(_cur).name}")
                    with st.spinner("🎬 Ajout hook animé..."):
                        _ok = add_hook_overlay(_cur, _out, content_package.hook, _ffmpeg)
                    if _ok:
                        _cur = _out
                    else:
                        st.warning("⚠️ Hook animé échoué — vidéo originale conservée.")

                if add_subs:
                    _out = str(_exp / f"sub_{Path(_cur).name}")
                    with st.spinner("📝 Ajout sous-titres..."):
                        _ok = add_subtitles_overlay(_cur, _out, voiceover, _ffmpeg)
                    if _ok:
                        _cur = _out
                    else:
                        st.warning("⚠️ Sous-titres échoués — vidéo originale conservée.")

                if add_music_opt and music_file_path:
                    _out = str(_exp / f"music_{Path(_cur).name}")
                    with st.spinner("🎵 Mixage musique de fond..."):
                        _ok = mix_music(_cur, music_file_path, _out, _ffmpeg, music_volume)
                    if _ok:
                        _cur = _out
                    else:
                        st.warning("⚠️ Mixage musique échoué — vidéo sans musique conservée.")

                enhanced_video = _cur
            else:
                st.warning("⚠️ ffmpeg non trouvé — overlays et musique désactivés.")

        export = write_publish_package(
            export_root=EXPORTS_DIR,
            account_profile=profile_dict,
            content=content_dict,
            media=media,
        )

        # ── Cerveau : sauvegarder la session ─────────────────────────────────
        if _brain is not None:
            _brain.save_session({
                "hook": content_package.hook,
                "title": content_package.title,
                "hashtags": content_package.hashtags,
                "keywords": [k.strip() for k in extra_keywords.split(",") if k.strip()],
                "score": content_score["global"],
                "niche": niche,
                "tone": tone,
                "audience": audience,
                "language": language,
                "topic": video_topic,
                "goal": goal,
            })

        # ── Stocker dans session_state pour persister après rerun ─────────────
        st.session_state["editai_results"] = {
            "content_package": content_package,
            "caption": caption,
            "variants": variants,
            "content_score": content_score,
            "voiceover": voiceover,
            "content_dict": content_dict,
            "export": export,
            "media": media,
            "opening_analysis_dict": opening_analysis_dict,
            "profile": profile,
            "enhanced_video": enhanced_video,
        }

    # ── Affichage résultats (toujours depuis session_state) ───────────────────
    res = st.session_state.get("editai_results")
    if res is None:
        return

    content_package    = res["content_package"]
    caption            = res["caption"]
    variants           = res["variants"]
    content_score      = res["content_score"]
    voiceover          = res["voiceover"]
    export             = res["export"]
    media              = res["media"]
    opening_analysis_dict = res["opening_analysis_dict"]
    profile            = res["profile"]
    enhanced_video     = res.get("enhanced_video", media["processed_video"])

    st.success("Package généré: prêt à publier sur TikTok")
    st.write("Fenêtre recommandée:", profile.best_posting_window)
    st.write("Qualité contenu:", f"{content_score['global']}/100 ({content_score['verdict']})")
    st.caption(media.get("adaptation_notes", "Adaptation standard appliquée"))

    if opening_analysis_dict is not None:
        st.subheader("Analyse ouverture")
        stat1, stat2, stat3, stat4, stat5 = st.columns(5)
        score_val = opening_analysis_dict['opening_score']
        stat1.metric("Score ouverture", f"{score_val}/100",
                     delta="fort" if score_val >= 75 else ("moyen" if score_val >= 55 else "faible"),
                     delta_color="normal" if score_val >= 75 else ("off" if score_val >= 55 else "inverse"))
        stat2.metric("Score 2 premières secondes",
                     f"{min(score_val + 5, 100)}/100" if opening_analysis_dict['black_intro_sec'] < 0.2 else f"{max(score_val - 15, 30)}/100")
        stat3.metric("Intro noire coupée", f"{opening_analysis_dict['black_intro_sec']} s")
        stat4.metric("Volume moyen", f"{opening_analysis_dict['mean_volume_db']} dB")
        stat5.metric("Durée source", f"{opening_analysis_dict['duration_sec']} s")

        st.markdown("**Recommandations appliquées automatiquement:**")
        for rec in opening_analysis_dict.get("recommendations", []):
            st.write(f"- {rec}")

    result_left, result_right = st.columns([1.15, 1], gap="large")

    with result_left:
        st.subheader("🎬 Vidéo préparée")
        video_file = Path(enhanced_video)
        if not video_file.exists():
            video_file = Path(media["processed_video"])  # fallback
        if video_file.exists():
            st.video(str(video_file))
            st.download_button(
                label="Télécharger vidéo prête",
                data=video_file.read_bytes(),
                file_name=video_file.name,
                mime="video/mp4",
                use_container_width=True,
            )

    with result_right:
        st.subheader("Texte TikTok")

        # Hook + bouton ⭐
        hook_col, star_col = st.columns([5, 1])
        with hook_col:
            hook_text = st.text_input("Hook", value=content_package.hook)
        with star_col:
            st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)
            if st.button("⭐", key="star_hook", help="Marquer ce hook comme bon"):
                if _brain is not None:
                    _brain.mark_good("hook", hook_text)
                st.toast("Hook mémorisé par le cerveau IA !", icon="⭐")
        copy_button(hook_text, "Copier hook", "copy-hook")

        # Titre + bouton ⭐
        title_col, star_col2 = st.columns([5, 1])
        with title_col:
            title_text = st.text_input("Titre", value=content_package.title)
        with star_col2:
            st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)
            if st.button("⭐", key="star_title", help="Marquer ce titre comme bon"):
                if _brain is not None:
                    _brain.mark_good("title", title_text)
                st.toast("Titre mémorisé par le cerveau IA !", icon="⭐")
        copy_button(title_text, "Copier titre", "copy-title")

        description_text = st.text_area("Description", value=content_package.description, height=110)
        copy_button(description_text, "Copier description", "copy-description")

        caption_text = st.text_area("Caption complète", value=caption, height=200)
        st.caption(f"Longueur caption: {len(caption_text)} caractères")
        copy_button(caption_text, "Copier caption", "copy-caption")

        st.markdown("### Variantes Hook + Titre")
        for idx, variant in enumerate(variants, start=1):
            v_col, v_star = st.columns([5, 1])
            with v_col:
                st.write(f"**V{idx}** Hook: {variant.hook}")
                st.write(f"**V{idx}** Titre: {variant.title}")
            with v_star:
                if st.button("⭐", key=f"star_v{idx}", help="Marquer cette variante comme bonne"):
                    if _brain is not None:
                        _brain.mark_good("hook", variant.hook)
                        _brain.mark_good("title", variant.title)
                    st.toast(f"Variante {idx} mémorisée !", icon="⭐")
            copy_button(
                f"{variant.hook}\n{variant.title}",
                f"Copier variante {idx}",
                f"copy-variant-{idx}",
            )

        st.markdown("### Script voix-off 8 secondes")
        st.caption("Lis ce script au rythme de la vidéo pour maximiser la rétention dès l'ouverture.")
        st.text_area("Script voix-off", value=voiceover, height=160)
        copy_button(voiceover, "Copier script voix-off", "copy-voiceover")

    st.subheader("Hashtags")
    hashtags_text = " ".join(content_package.hashtags)
    ht_col, ht_star = st.columns([6, 1])
    with ht_col:
        st.text_area("Hashtags prêts à coller", value=hashtags_text, height=80)
    with ht_star:
        st.markdown("<div style='margin-top:28px'></div>", unsafe_allow_html=True)
        if st.button("⭐", key="star_tags", help="Mémoriser ces hashtags"):
            if _brain is not None:
                _brain.mark_good("hashtags", hashtags_text)
            st.toast("Hashtags mémorisés !", icon="⭐")
    copy_button(hashtags_text, "Copier hashtags", "copy-tags")

    caption_file = Path(export["caption_file"])
    st.download_button(
        label="Télécharger caption.txt",
        data=caption_file.read_text(encoding="utf-8"),
        file_name="caption.txt",
        mime="text/plain",
        use_container_width=True,
    )

    payload_file = Path(export["payload_file"])
    st.download_button(
        label="Télécharger publish_payload.json",
        data=payload_file.read_text(encoding="utf-8"),
        file_name="publish_payload.json",
        mime="application/json",
        use_container_width=True,
    )

    st.info(f"Package complet: {export['package_dir']}")


if __name__ == "__main__":
    main()

