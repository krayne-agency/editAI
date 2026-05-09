from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def write_publish_package(
    export_root: Path,
    account_profile: dict[str, Any],
    content: dict[str, Any],
    media: dict[str, str],
) -> dict[str, str]:
    export_root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    package_dir = export_root / f"tiktok_package_{timestamp}"
    package_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "profile": account_profile,
        "content": content,
        "media": media,
        "status": "ready_to_publish",
    }

    payload_file = package_dir / "publish_payload.json"
    payload_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    caption_file = package_dir / "caption.txt"
    caption_text = content.get("caption", "")
    caption_file.write_text(caption_text, encoding="utf-8")

    checklist_file = package_dir / "checklist.md"
    checklist_file.write_text(
        "\n".join(
            [
                "# Checklist publication TikTok",
                "",
                "- [ ] Vérifier la miniature proposée",
                "- [ ] Coller le titre et la description générés",
                "- [ ] Vérifier les hashtags",
                "- [ ] Activer les options de commentaires",
                "- [ ] Publier dans la fenêtre recommandée",
            ]
        ),
        encoding="utf-8",
    )

    return {
        "package_dir": str(package_dir),
        "payload_file": str(payload_file),
        "caption_file": str(caption_file),
        "checklist_file": str(checklist_file),
    }
