
# 🪔 Rama Bhakt 

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)
![PySide6](https://img.shields.io/badge/PySide6-6.12%2B-green?style=for-the-badge&logo=qt)
![OpenAI](https://img.shields.io/badge/OpenAI-API-orange?style=for-the-badge&logo=openai)
![SQLite](https://img.shields.io/badge/SQLite-3-lightgrey?style=for-the-badge&logo=sqlite)
![Platform](https://img.shields.io/badge/Platform-Windows-lightblue?style=for-the-badge&logo=windows)

**Rama Bhakt** is a private, voice-enabled desktop application built as a digital Diwali gift for families. 

It serves as a warm, wise, and familiar spiritual companion inspired by the qualities of Lord Rama and Hanuman. It is designed to encourage family unity, personal reflection, and meaningful intergenerational conversations—nurturing a personal relationship with the Divine in everyday life, beyond mere rituals.

## ✨ Features

*   **🗣️ The Evening Call:** A conversational voice experience using OpenAI's TTS and STT. Speak naturally and listen to warm, thoughtful responses.
*   **📖 Ramayana Storytelling:** Immersive storytelling and Q&A based *strictly* on a locally indexed PDF of the Valmiki Ramayana (using local RAG and vector search). The app clearly distinguishes between the source text and creative storytelling.
*   **🧠 Structured Memory:** Remembers useful, non-sensitive preferences and topics between calls to build genuine continuity, while allowing users to review and delete memories.
*   **🪔 Family Gatherings:** A scheduled "ring" that gently chimes at a random time within a family-set window (e.g., 7:30 PM - 7:40 PM), inviting the family to gather for a guided spiritual reflection on their day.
*   **🎨 Beautiful, Calm UI:** Native PySide6 interface featuring 5 serene themes (Warm Saffron, Indigo Night, Lotus Pink, Forest Sanctuary, Dusk Gold), custom background image support, and adjustable text sizes.
*   **🔒 Privacy-First:** All conversations and memories are stored locally in SQLite. No background listening, no telemetry, and no analytics. API keys are secured via Windows Credential Manager.

## 🛠️ Technology Stack

*   **UI:** PySide6 (Qt for Python) with QSS theming.
*   **Intelligence:** OpenAI (`gpt-4o-mini` for text, `gpt-4o-mini-tts` for voice, `gpt-4o-mini-transcribe` for speech-to-text).
*   **Database:** SQLite (with FTS5 for memory retrieval).
*   **RAG (Retrieval-Augmented Generation):** Local PDF ingestion via `pypdf`, embeddings via `text-embedding-3-small`, and cosine similarity search using `numpy` (no heavyweight vector databases required).
*   **Security:** `keyring` for Windows Credential Manager integration.

## 🚀 Getting Started (Developer Setup)

### Prerequisites
*   Windows 10/11
*   Python 3.10 or higher
*   An OpenAI API Key

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/rama-bhakt.git
   cd rama-bhakt
   ```

2. **Create and activate a virtual environment:**
   ```powershell
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   pip install pyinstaller
   ```

4. **Set up your API Key (Developer):**
   ```powershell
   python tools\set_family.py key family_demo
   ```

5. **Ingest the Ramayana PDF (One-time setup):**
   Place your Ramayana PDF in the project root and run:
   ```powershell
   python tools\ingest_pdf.py path/to/ramayana.pdf --title "Valmiki Ramayana"
   ```
   *(This creates `data/ramayana.db`, which is required for Story mode).*

6. **Run the application:**
   ```powershell
   python main.py
   ```

## 📦 Packaging for Distribution

This app is designed to be packaged as a standalone Windows executable for specific families.

1. Create a family profile:
   ```powershell
   python tools\set_family.py new family_name
   ```
2. Edit `config/families/family_name.json` to add their specific API key, custom prompts, and preferences.
3. Build the app:
   ```powershell
   build\build_family.bat family_name
   ```
4. The installer will be generated in `dist_installers\`.

## ⚠️ Important Disclaimers

*   **AI Nature:** The companion is an AI. It is not the actual divine personality, nor is it an authorised spiritual authority. It is a tool designed to inspire reflection and conversation.
*   **No Affiliation:** This application is a personal gift and is not officially affiliated with, endorsed by, or representing any religious organisation, temple, or mission.
*   **Privacy & Security:** While API keys are stored securely on the local machine, a key distributed inside a desktop application cannot be guaranteed secret from someone with sufficient admin access to the computer. It is highly recommended to use per-family API keys with strict monthly spending limits configured in the OpenAI dashboard.
*   **Copyright:** The `ramayana.db` generated during setup contains text derived from the provided PDF. Ensure you have the right to distribute the compiled index before sharing the application.

## 🙏 Acknowledgements

Built with love, for family, and for the light of Diwali. 

*"Selfless Action. We envision a world where every individual has the opportunity to reach their full potential..."*
```
