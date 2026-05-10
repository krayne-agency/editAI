from __future__ import annotations

import json
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
from core.gemini_ai import analyze_account as _gemini_analyze_account
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
_SETTINGS_FILE = ROOT / "workspace_data" / "settings.json"
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

/* ── Bouton réouverture sidebar — natif + fallback ──────────────────────── */
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"],
button[aria-label="Open sidebar"],
button[title="Open sidebar"],
button[aria-label="Ouvrir le panneau latéral"],
section[data-testid="stSidebarCollapsedControl"] {
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    z-index: 999999 !important;
}
/* Bouton flottant custom */
#editai-sidebar-toggle {
    position: fixed;
    left: 8px;
    top: 50%;
    transform: translateY(-50%);
    z-index: 999999;
    background: #0d1424;
    border: 1px solid #1e3a5f;
    border-radius: 0 8px 8px 0;
    color: #83FFC7;
    width: 26px;
    height: 48px;
    cursor: pointer;
    font-size: 16px;
    display: none;
    align-items: center;
    justify-content: center;
    transition: background 0.15s;
}
#editai-sidebar-toggle:hover { background: #1e3a5f; }

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


def _load_settings() -> dict:
    try:
        if _SETTINGS_FILE.exists():
            return json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        pass
    return {}


def _save_settings(data: dict) -> None:
    _SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    existing = _load_settings()
    existing.update(data)
    _SETTINGS_FILE.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")


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

    # ── Bouton flottant pour rouvrir la sidebar + bouton ❮ pour la fermer ──
    components.html("""
<script>
(function() {
  var pd = window.parent.document;
  var wp = window.parent;

  // ── Bouton "❮" injectable dans la sidebar pour la fermer ──────────────
  function injectCloseBtn() {
    var sidebar = pd.querySelector('[data-testid="stSidebar"]');
    if (!sidebar || pd.getElementById('editai-close-btn')) return;
    sidebar.style.position = 'relative';
    var cb = pd.createElement('button');
    cb.id = 'editai-close-btn';
    cb.innerHTML = '&#10094;';
    cb.title = 'Fermer le panneau';
    cb.style.cssText = [
      'position:absolute','top:10px','right:8px','z-index:2147483647',
      'background:#1e3a5f','border:none','border-radius:6px',
      'color:#83FFC7','width:28px','height:28px','cursor:pointer',
      'font-size:15px','display:flex','align-items:center','justify-content:center',
      'transition:background 0.15s','padding:0'
    ].join(';');
    cb.onmouseover = function() { cb.style.background = '#0f2744'; };
    cb.onmouseout  = function() { cb.style.background = '#1e3a5f'; };
    cb.onclick = function() {
      var sels = [
        '[data-testid="stSidebarCollapseButton"] button',
        'button[aria-label="Collapse sidebar"]',
        'button[aria-label="R\u00e9duire le panneau lat\u00e9ral"]',
        '[data-testid="stSidebarHeader"] button',
      ];
      for (var i = 0; i < sels.length; i++) {
        var n = pd.querySelector(sels[i]);
        if (n) { n.click(); return; }
      }
    };
    sidebar.insertBefore(cb, sidebar.firstChild);
  }

  // ── Bouton flottant "☰" pour rouvrir quand la sidebar est fermée ──────
  if (!pd.getElementById('editai-toggle-btn')) {
    var btn = pd.createElement('button');
    btn.id = 'editai-toggle-btn';
    btn.innerHTML = '&#9776;';
    btn.title = 'Ouvrir le panneau IA';
    btn.style.cssText = [
      'position:fixed', 'left:0', 'top:50%', 'transform:translateY(-50%)',
      'z-index:2147483647', 'background:#0d1424', 'border:1px solid #1e3a5f',
      'border-radius:0 8px 8px 0', 'color:#83FFC7', 'width:26px', 'height:48px',
      'cursor:pointer', 'font-size:16px', 'display:none', 'align-items:center',
      'justify-content:center', 'transition:background 0.15s', 'padding:0'
    ].join(';');
    btn.onmouseover = function() { btn.style.background = '#1e3a5f'; };
    btn.onmouseout  = function() { btn.style.background = '#0d1424'; };
    btn.onclick = function() {
      var sel = [
        '[data-testid="stSidebarCollapsedControl"] button',
        '[data-testid="collapsedControl"] button',
        'button[aria-label="Open sidebar"]',
        'button[aria-label="Ouvrir le panneau lat\u00e9ral"]',
        '[data-testid="stSidebarCollapsedControl"]',
      ];
      for (var i = 0; i < sel.length; i++) {
        var n = pd.querySelector(sel[i]);
        if (n) { n.click(); break; }
      }
    };
    pd.body.appendChild(btn);
  }

  // Intervalle — survit aux re-renders Streamlit
  if (!wp._editaiToggleInterval) {
    wp._editaiToggleInterval = setInterval(function() {
      var b = pd.getElementById('editai-toggle-btn');
      if (!b) { clearInterval(wp._editaiToggleInterval); wp._editaiToggleInterval = null; return; }
      var collapsed = pd.querySelector(
        '[data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"]'
      );
      b.style.display = collapsed ? 'flex' : 'none';
      if (!collapsed) injectCloseBtn();
    }, 350);
  }
})();
</script>
""", height=1)

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
        # ── Pré-remplissage depuis settings.json puis brain ─────────────────
        _settings = _load_settings()
        _brain_defaults: dict = {}
        if _brain is not None:
            _brain_defaults = _brain.load_profile()

        st.markdown("**Profil compte**")
        account_name = st.text_input(
            "Nom du compte",
            value=_settings.get("account_name", "") or "MonCompte",
        )
        niche = st.text_input(
            "Niche",
            value=_settings.get("niche", "") or _brain_defaults.get("niche", "") or "Marketing digital",
        )
        audience = st.text_input(
            "Audience",
            value=_settings.get("audience", "") or _brain_defaults.get("audience", "") or "18-34 ans",
        )
        _tone_opts = ["dynamique", "expert", "amical", "premium"]
        _saved_tone = _settings.get("tone") or _brain_defaults.get("tone", "dynamique")
        _tone_idx = _tone_opts.index(_saved_tone) if _saved_tone in _tone_opts else 0
        tone = st.selectbox("Ton", _tone_opts, index=_tone_idx)
        _lang_opts = ["fr", "en"]
        _saved_lang = _settings.get("language", "fr")
        _lang_idx = _lang_opts.index(_saved_lang) if _saved_lang in _lang_opts else 0
        language = st.selectbox("Langue", _lang_opts, index=_lang_idx)
        post_frequency = st.text_input(
            "Fréquence",
            value=_settings.get("post_frequency", "") or "1 vidéo/jour",
        )
        if st.button("💾 Sauver le profil", key="btn_save_profile", use_container_width=True):
            _save_settings({
                "account_name": account_name,
                "niche": niche,
                "audience": audience,
                "tone": tone,
                "language": language,
                "post_frequency": post_frequency,
            })
            st.success("Profil sauvegardé ✅")
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

        # ── Analyse de compte IA ──────────────────────────────────────────
        st.divider()
        st.markdown("**📊 Analyse de compte**")
        if st.button("🔍 Analyser mon compte", key="btn_analyze_account", use_container_width=True):
            if not gemini_key.strip():
                st.warning("⚠️ Clé Gemini requise pour l'analyse de compte.")
            elif _brain is None or _brain.get_stats()["sessions"] == 0:
                st.info("💡 Lance au moins une analyse vidéo pour que le cerveau puisse apprendre ton style.")
            else:
                with st.spinner("Analyse de ton compte en cours…"):
                    _brain_ctx = _brain.get_brain_context(niche=niche, tone=tone)
                    _account_analysis = _gemini_analyze_account(
                        niche=niche, tone=tone, audience=audience,
                        language=language, brain_context=_brain_ctx, api_key=gemini_key,
                    )
                if _account_analysis:
                    st.session_state["account_analysis"] = _account_analysis
                else:
                    st.error("Analyse impossible — vérifie ta clé Gemini.")

        _acct = st.session_state.get("account_analysis")
        if _acct:
            st.markdown(
                f'<div style="background:#0f1e35;border:1px solid #1e3a5f;border-radius:10px;padding:10px 12px;margin-top:6px;">'
                f'<div style="color:#83FFC7;font-weight:700;font-size:0.8rem;margin-bottom:6px;">✅ Points forts</div>'
                f'<div style="color:#cbd5e1;font-size:0.75rem;">{_acct.get("strengths","")}</div>'
                f'<div style="color:#f59e0b;font-weight:700;font-size:0.8rem;margin:8px 0 4px;">⚠️ Axes d\'amélioration</div>'
                f'<div style="color:#cbd5e1;font-size:0.75rem;">{_acct.get("gaps","")}</div>'
                f'<div style="color:#38bdf8;font-weight:700;font-size:0.8rem;margin:8px 0 4px;">🎯 Prochaine vidéo idéale</div>'
                f'<div style="color:#e2e8f0;font-size:0.75rem;font-weight:600;">{_acct.get("next_content","")}</div>'
                f'<div style="color:#a78bfa;font-weight:700;font-size:0.8rem;margin:8px 0 4px;">🪝 Formule hook optimale</div>'
                f'<div style="color:#e2e8f0;font-size:0.75rem;font-style:italic;">{_acct.get("hook_formula","")}</div>'
                f'<div style="color:#4ade80;font-weight:700;font-size:0.8rem;margin:8px 0 4px;">🚀 Conseil croissance #1</div>'
                f'<div style="color:#cbd5e1;font-size:0.75rem;">{_acct.get("growth_tip","")}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # ── Dossier d'export personnalisé ──────────────────────────────────
        st.divider()
        st.markdown("⚙️ **Export auto**")
        _s = _load_settings()
        _custom_folder_val = _s.get("export_folder", "")
        custom_export_folder = st.text_input(
            "Copier la vidéo vers...",
            value=_custom_folder_val,
            placeholder=str(EXPORTS_DIR),
            key="custom_export_folder",
            help="Définis un dossier perso pour retrouver chaque export automatiquement",
        )
        if st.button("💾 Sauver le dossier", key="btn_save_export_folder", use_container_width=True):
            _save_settings({"export_folder": custom_export_folder.strip()})
            st.toast("📁 Dossier sauvegardé !", icon="✅")

    col1, col2 = st.columns([1.2, 1])

    with col1:
        st.subheader("1) Vidéo")
        uploaded_video = st.file_uploader("Choisis la vidéo source", type=["mp4", "mov", "mkv", "avi"])
        video_topic = st.text_input("Sujet de la vidéo", value="Astuce croissance TikTok")
        goal = st.selectbox("Objectif", ["engagement", "vues", "conversion", "abonnés"])
        style = st.selectbox(
            "Style de contenu",
            ["standard", "gaming_viral", "educatif", "business", "lifestyle"],
            format_func=lambda s: {
                "standard": "⚡ Standard TikTok",
                "gaming_viral": "🎮 Gaming Viral",
                "educatif": "📚 Éducatif",
                "business": "💼 Business / Entreprise",
                "lifestyle": "✨ Lifestyle / Esthétique",
            }.get(s, s),
        )
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
            # Import direct depuis l'UI
            uploaded_music = st.file_uploader(
                "Importe une musique (.mp3 / .wav)",
                type=["mp3", "wav", "aac", "m4a"],
                key="music_upload",
                help="Ou dépose des fichiers dans workspace_data/music/ pour les retrouver à chaque session",
            )
            if uploaded_music is not None:
                _music_save = ROOT / "workspace_data" / "music" / uploaded_music.name
                _music_save.parent.mkdir(parents=True, exist_ok=True)
                _music_save.write_bytes(uploaded_music.getbuffer())
                music_file_path = str(_music_save)
                st.success(f"🎵 {uploaded_music.name} chargée")
                library = get_music_library()  # rafraîchir
            if music_file_path is None and library:
                choices = {f.name: str(f) for f in library}
                chosen = st.selectbox("Ou choisis dans la bibliothèque", list(choices.keys()), key="music_select")
                music_file_path = choices[chosen]
            if music_file_path is None and not library:
                st.caption("Importe une musique ci-dessus pour commencer.")
                add_music_opt = False
            if music_file_path is not None:
                music_volume = float(st.slider("Volume musique (dB)", -35, -5, -20, key="music_vol",
                                               help="-30 = très discret · -20 = fond · -10 = présent"))

        run = st.button("Analyser et préparer", type="primary", use_container_width=True)

    with col2:
        st.subheader("Aperçu 9:16")
        if uploaded_video is not None:
            # ── Sauvegarde sur disque ──────────────────────────────────────────
            _preview_path = UPLOADS_DIR / uploaded_video.name
            UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
            if not _preview_path.exists():
                with st.spinner("Enregistrement de la vidéo…"):
                    _preview_path.write_bytes(uploaded_video.getbuffer())
            uploaded_video.seek(0)

            # ── Copie vers app/static/ (servie par Streamlit à /app/static/) ──
            _static_dir = Path(__file__).resolve().parent / "static"
            _static_dir.mkdir(exist_ok=True)
            _vid_ext = Path(uploaded_video.name).suffix.lower() or ".mp4"
            _static_video = _static_dir / f"preview_video{_vid_ext}"
            # Recopy si taille différente (nouvelle vidéo)
            if not _static_video.exists() or _static_video.stat().st_size != _preview_path.stat().st_size:
                import shutil as _shutil
                _shutil.copy2(str(_preview_path), str(_static_video))
            _video_url = f"/app/static/preview_video{_vid_ext}"

            # ── Frame téléphone 9:16 avec vidéo à l'intérieur ─────────────────
            components.html(f"""
<div style="display:flex;flex-direction:column;align-items:center;gap:6px;
            font-family:sans-serif;padding:4px 0;">
  <span style="background:#0f766e;color:#fff;border-radius:6px;
               padding:3px 12px;font-size:0.72rem;font-weight:700;letter-spacing:.5px;">
    &#9654; Aperçu rendu final · 1080&times;1920
  </span>
  <!-- Boîtier téléphone -->
  <div style="
    position:relative;
    width:162px; height:288px;
    border:2px solid #1e3a5f;
    border-radius:24px;
    background:#000;
    box-shadow:0 0 24px #0a0f1a, 0 0 0 5px #0d1424, inset 0 0 0 1px #0f2040;
    overflow:hidden;
  ">
    <!-- Notch -->
    <div style="position:absolute;top:6px;left:50%;transform:translateX(-50%);
                width:38px;height:4px;background:#1e2d45;border-radius:3px;z-index:4;pointer-events:none;"></div>
    <!-- Vidéo portrait plein-écran : cover = zoom+crop côtés, avec son -->
    <video
      src="{_video_url}"
      controls playsinline
      style="
        position:absolute;top:0;left:0;
        width:100%;height:100%;
        object-fit:cover;
        border-radius:22px;
        z-index:2;
      ">
    </video>
    <!-- Overlay dégradé bas TikTok -->
    <div style="
      position:absolute;bottom:0;left:0;right:0;height:60px;
      background:linear-gradient(transparent,rgba(0,0,0,.6));
      border-radius:0 0 22px 22px;z-index:3;pointer-events:none;
    "></div>
  </div>
  <span style="color:#64748b;font-size:0.65rem;text-align:center;">
    ▶ Aperçu · 9:16 · son actif
  </span>
</div>
""", height=340)

        else:
            st.markdown(
                """
<div style="display:flex;flex-direction:column;align-items:center;gap:8px;">
  <div style="
    width:162px; height:288px;
    border:2px solid #1e3a5f; border-radius:24px;
    background:#0d1424; display:flex; align-items:center; justify-content:center;
    box-shadow:0 0 24px #0a0f1a, 0 0 0 5px #0d1424;
  ">
    <div style="text-align:center;">
      <div style="color:#1e3a5f;font-size:2rem;margin-bottom:8px;">&#9654;</div>
      <div style="color:#334155;font-size:0.65rem;">9:16 · TikTok Ready</div>
    </div>
  </div>
  <span style="color:#64748b;font-size:0.72rem;">Importe une vidéo pour voir l&apos;aperçu</span>
</div>""",
                unsafe_allow_html=True,
            )

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
            style=style,
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
            # Badge résolution + son
            _has_aud = media.get("has_audio", True)
            _aud_label = "🔊 Son conservé" if _has_aud else "🔇 Muet (source sans audio)"
            st.markdown(
                f'<div style="display:flex;gap:8px;margin-bottom:6px;">'  
                f'<span style="background:#0f766e;color:#fff;border-radius:6px;padding:2px 10px;font-size:0.72rem;font-weight:700;">'
                f'✅ 1080×1920 · 9:16</span>'  
                f'<span style="background:#1e3a5f;color:#e2e8f0;border-radius:6px;padding:2px 10px;font-size:0.72rem;">'  
                f'{_aud_label}</span></div>',
                unsafe_allow_html=True,
            )
            st.video(str(video_file))
            st.download_button(
                label="Télécharger vidéo prête",
                data=video_file.read_bytes(),
                file_name=video_file.name,
                mime="video/mp4",
                use_container_width=True,
            )
            # Auto-copie vers dossier perso
            _saved_folder = _load_settings().get("export_folder", "").strip()
            if _saved_folder:
                _dest_dir = Path(_saved_folder)
                if _dest_dir.exists() and _dest_dir.is_dir():
                    import shutil as _shutil
                    _dest_file = _dest_dir / video_file.name
                    try:
                        _shutil.copy2(str(video_file), str(_dest_file))
                        st.info(f"📁 Copié dans : `{_dest_file}`")
                    except Exception as _e:
                        st.warning(f"⚠️ Copie impossible : {_e}")
                else:
                    st.warning(f"⚠️ Dossier d'export introuvable : `{_saved_folder}`")

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

