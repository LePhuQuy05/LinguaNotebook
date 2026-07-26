# 🦉 LinguaNotebook

**The open-source language learning platform powered by your own documents.**

[![CI](https://github.com/LePhuQuy05/LinguaNotebook/actions/workflows/ci.yml/badge.svg)](https://github.com/LePhuQuy05/LinguaNotebook/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Upload your foreign-language PDFs, and LinguaNotebook automatically parses them into structured, searchable content. Create a study schedule, and get personalized daily lessons — flashcards, reading comprehension, grammar exercises, and listening practice with multilingual text-to-speech. Works fully offline. 100% free.

## Features

- **Document Parsing**: Upload PDFs in any language. HPD-Parsing extracts structured content with headings, tables, and text blocks.
- **Smart Knowledge Base**: All your documents are indexed with hybrid search (semantic + keyword). Find anything instantly.
- **Daily Lessons**: Auto-generated flashcards, reading passages, grammar exercises, and listening practice from your own materials.
- **Text-to-Speech**: Hear any word, sentence, or passage in 8+ languages. Works offline.
- **Spaced Repetition**: SM-2 algorithm schedules reviews at optimal intervals.
- **Offline-First**: Full learning experience without internet. Syncs when you reconnect.
- **Cross-Platform**: Web app + native iOS and Android apps.
- **100% Free**: No paywalls, no premium tiers. Open source under MIT license.
- **Self-Hostable**: Run your own instance with Docker Compose.

## Quick Start

### Cloud Version

Visit **[linguanotebook.app](https://linguanotebook.app)** (coming soon)

### Self-Hosted (Docker)

```bash
git clone https://github.com/LePhuQuy05/LinguaNotebook.git
cd LinguaNotebook
cp .env.example .env
docker compose -f docker/docker-compose.yml up -d
```

Open http://localhost:3000

### Development

See the [Quickstart Guide](specs/001-lingua-notebook/quickstart.md) for detailed dev setup.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI, Celery, SQLAlchemy |
| Frontend | Next.js 14, TypeScript, Tailwind CSS, shadcn/ui |
| Mobile | React Native + Expo |
| Database | PostgreSQL 15, Qdrant (vector), Redis |
| ML | HPD-Parsing, BGE-M3, Edge TTS, Piper TTS |
| Infrastructure | Docker, GitHub Actions |

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT — see [LICENSE](LICENSE)
