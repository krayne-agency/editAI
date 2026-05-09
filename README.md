# editAI

Application locale IA pour préparer des vidéos TikTok en mode prêt à publier.

Fonctionnalités principales:

- Analyse rapide de ton profil compte (niche, audience, ton, fréquence, données CSV optionnelles).
- Traitement automatique vidéo pour format TikTok 9:16 (1080x1920, H264, AAC).
- Génération automatique hook, titre, description, hashtags et CTA.
- Variantes hook/titre pour faire un choix rapide avant publication.
- Score de potentiel d'accroche (hook, titre, hashtags).
- Boutons copier pour hook, titre, description, caption et hashtags.
- Mode analyse ouverture (3 premieres secondes) avec adaptation automatique.
- Export d'un package publication avec:
	- vidéo finale
	- miniature
	- caption.txt
	- publish_payload.json
	- checklist de publication

Adaptation vidéo appliquée automatiquement:

- Format vertical TikTok 9:16 en 1080x1920.
- Framerate stabilisé à 30 fps.
- Encodage H264 + AAC compatible mobile.
- Audio normalisé pour un volume plus constant.
- Durée plafonnée à 35 secondes pour favoriser la rétention initiale.
- Coupe automatique de l'intro noire détectée.
- Renforcement dynamique image/audio si score d'ouverture faible.

Analyse ouverture:

- Analyse des 3 premieres secondes (intro noire, volume, cadence, format).
- Score ouverture sur 100 + recommandations actionnables.
- Le traitement video s'adapte a ce diagnostic.

Important:

- L'application ne publie pas automatiquement. Le post TikTok reste manuel pour garder un comportement naturel du compte.

## Installation

1. Installer Python 3.11+
2. Installer ffmpeg et l'ajouter au PATH
3. Installer les dépendances:

	 pip install -r requirements.txt

## Lancer l'application

Depuis la racine du projet:

streamlit run app/main.py

Ou en mode autonome Windows (recommande):

start_editai.bat

Ce lanceur:

- detecte Python (py ou python)
- cree automatiquement un venv local
- installe/maj les dependances
- lance l'application

## Utilisation

1. Renseigne ton profil dans la sidebar.
2. Charge une vidéo.
3. Clique sur Analyser et préparer.
4. Télécharge la vidéo optimisée + fichiers texte.
5. Publie directement dans TikTok avec les éléments générés.

## Arborescence

- app/main.py: interface Streamlit
- app/core/profile_analyzer.py: analyse de profil
- app/core/video_engine.py: normalisation vidéo TikTok
- app/core/content_engine.py: génération hook/titre/caption
- app/core/exporter.py: export package prêt à publier
