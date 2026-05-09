"""
launcher.py - Lance EditAI comme une vraie application Windows.
Streamlit tourne en arrière-plan, pywebview ouvre une fenêtre native.
"""
from __future__ import annotations

import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

# ── Log fichier (capte les crashs en mode pythonw) ──────────────────────────
_LOG = Path(__file__).resolve().parent / "editai.log"
try:
    _log_f = open(_LOG, "w", encoding="utf-8")  # noqa: WPS515
    sys.stdout = _log_f
    sys.stderr = _log_f
except Exception:
    pass


def _find_free_port(start: int = 8501, end: int = 8600) -> int:
    """Trouve un port TCP libre dans la plage donnée."""
    for port in range(start, end):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return start  # fallback


def _make_icon() -> str | None:
    """Génère app/assets/icon.ico si absent. Retourne le chemin ou None."""
    icon_path = Path(__file__).resolve().parent / "app" / "assets" / "icon.ico"
    if icon_path.exists():
        return str(icon_path)
    try:
        from PIL import Image, ImageDraw  # type: ignore[import]

        sizes = [16, 32, 48, 64, 128, 256]
        images: list[Image.Image] = []

        for sz in sizes:
            img = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)

            # ── Fond arrondi sombre ──────────────────────────────────────
            r = max(3, sz // 5)
            d.rounded_rectangle([0, 0, sz - 1, sz - 1], radius=r, fill=(10, 15, 26, 255))

            teal = (131, 255, 199, 255)
            cyan = (56, 189, 248, 210)

            # ── Lettre E ────────────────────────────────────────────────
            lw = max(1, sz // 14)
            ex = sz // 8
            ew = sz * 11 // 32
            ey_top = sz // 7
            ey_bot = sz * 6 // 7
            ey_mid = (ey_top + ey_bot) // 2

            d.rectangle([ex, ey_top, ex + ew, ey_top + lw * 2], fill=teal)
            d.rectangle([ex, ey_mid - lw, ex + ew - lw * 2, ey_mid + lw], fill=teal)
            d.rectangle([ex, ey_bot - lw * 2, ex + ew, ey_bot], fill=teal)
            d.rectangle([ex, ey_top, ex + lw * 2, ey_bot], fill=teal)

            # ── Éclair ──────────────────────────────────────────────────
            bx = sz * 13 // 24
            pts = [
                bx + sz // 7,  sz // 8,
                bx - sz // 16, sz * 9 // 20,
                bx + sz // 14, sz * 9 // 20,
                bx - sz // 7,  sz * 7 // 8,
                bx + sz * 3 // 16, sz * 11 // 20,
                bx + sz // 16, sz * 11 // 20,
                bx + sz * 3 // 16, sz // 8,
            ]
            d.polygon(pts, fill=cyan)

            images.append(img)

        icon_path.parent.mkdir(parents=True, exist_ok=True)
        images[0].save(
            str(icon_path),
            format="ICO",
            sizes=[(s, s) for s in sizes],
            append_images=images[1:],
        )
        return str(icon_path)
    except Exception:  # noqa: BLE001
        return None


def _start_streamlit(port: int) -> subprocess.Popen:
    """Démarre le serveur Streamlit en sous-processus silencieux."""
    app_main = Path(__file__).resolve().parent / "app" / "main.py"

    cmd = [
        sys.executable, "-m", "streamlit", "run", str(app_main),
        "--server.headless=true",
        f"--server.port={port}",
        "--browser.gatherUsageStats=false",
        "--server.address=127.0.0.1",
    ]

    return subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )


def _wait_for_server(port: int, timeout: float = 30.0) -> bool:
    """Attend que le serveur Streamlit soit prêt."""
    import urllib.request
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}", timeout=1)
            return True
        except Exception:
            time.sleep(0.4)
    return False


def main() -> None:
    import webview  # type: ignore[import]

    # Icône barre des tâches Windows : définir l'AppUserModelID AVANT webview
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("EditAI.TikTokReady.1")
    except Exception:
        pass

    port = _find_free_port()
    icon_path = _make_icon()
    proc = _start_streamlit(port)

    # Fenêtre de chargement immédiate
    loading_html = """
    <html><body style="margin:0;background:#0a0f1a;display:flex;align-items:center;
    justify-content:center;height:100vh;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
    color:#83FFC7;flex-direction:column;gap:16px;">
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="80" height="80">
      <defs>
        <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" style="stop-color:#0f766e"/><stop offset="100%" style="stop-color:#083344"/>
        </linearGradient>
        <linearGradient id="sp" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" style="stop-color:#83FFC7"/><stop offset="100%" style="stop-color:#38bdf8"/>
        </linearGradient>
      </defs>
      <rect width="200" height="200" rx="40" ry="40" fill="url(#bg)"/>
      <rect x="38" y="52" width="52" height="12" rx="6" fill="url(#sp)"/>
      <rect x="38" y="94" width="42" height="12" rx="6" fill="url(#sp)"/>
      <rect x="38" y="136" width="52" height="12" rx="6" fill="url(#sp)"/>
      <rect x="38" y="52" width="12" height="96" rx="6" fill="url(#sp)"/>
      <polygon points="118,48 100,108 116,108 98,158 144,90 124,90 142,48" fill="url(#sp)" opacity="0.95"/>
    </svg>
    <div style="font-size:2rem;font-weight:800;letter-spacing:-1px;background:linear-gradient(135deg,#83FFC7,#38bdf8);
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;">EditAI</div>
    <div style="font-size:0.85rem;color:#475569;letter-spacing:1px;">Chargement en cours...</div>
    </body></html>
    """

    window = webview.create_window(
        title="EditAI",
        html=loading_html,
        width=1280,
        height=800,
        min_size=(900, 600),
        resizable=True,
    )

    def _load_app() -> None:
        ready = _wait_for_server(port, timeout=30.0)
        if ready:
            window.load_url(f"http://127.0.0.1:{port}")
        else:
            window.load_html(
                "<html><body style='background:#0e1117;color:#ff4b4b;font-family:sans-serif;"
                "display:flex;align-items:center;justify-content:center;height:100vh;'>"
                "<div>Erreur: impossible de démarrer le serveur.</div></body></html>"
            )

    threading.Thread(target=_load_app, daemon=True).start()

    try:
        webview.start(debug=False, icon=icon_path)
    finally:
        proc.terminate()


if __name__ == "__main__":
    main()
