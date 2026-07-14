# AI Investment OS — IDX Edition

AI investment research platform untuk pasar saham Indonesia (BEI/IDX).
Bukan trading bot: sistem mengumpulkan data lewat pipeline, menjalankan
*Investment Committee* multi-analis, membatasi keputusan dengan rule engine,
lalu menyajikan rekomendasi **beserta alasan, evidence, dan confidence** —
antarmuka pertama: Telegram.

Desain lengkap (6 fase, 43 dokumen) ada di [`docs/`](docs/README.md).
Keputusan arsitektur tercatat di [`docs/adr/`](docs/adr/).

## Status

Tahap 0 → M3 (lihat [milestones](docs/fase-6-delivery/04-milestones.md)):
fondasi core berjalan penuh secara offline di atas fixture knowledge base.

| Komponen | Status |
|---|---|
| Graph runtime (committee workflow, conditional edges, audit trail) | ✅ |
| Analis deterministik: technical, fundamental, news, foreign flow | ✅ |
| Bull/Bear case + konsensus komite | ✅ |
| Decision Engine (rule R1/R1b/R2/R3, override audit) | ✅ |
| Confidence Engine (evidence, freshness, agreement, kalibrasi) | ✅ |
| News pipeline (dedup, near-dup, reliability & importance scoring) | ✅ |
| Market Brief harian | ✅ |
| Telegram bot (long polling) | ✅ |
| Analis berbasis LLM, data provider nyata, Postgres/vector store | ⬜ port sudah tersedia |

## Quickstart

```bash
make install        # uv venv + install dev deps
make check          # ruff + mypy + pytest
make demo           # brief + analisis BBCA & ANTM dari fixture offline
```

Contoh langsung:

```bash
uv run investment-os analyze ANTM   # kasus konflik sinyal → rule R1 memaksa HOLD
uv run investment-os brief
```

Menjalankan bot Telegram (butuh token dari @BotFather):

```bash
cp .env.example .env                # isi INVOS_TELEGRAM_BOT_TOKEN
uv run investment-os serve-telegram
```

## Arsitektur

```
interfaces/telegram   adapter tipis: router → presenter → Bot API
        │
core/                 service (graph wiring) · agents · decision · confidence
                      explain · market_intel      ← tidak mengimpor interfaces
        │
knowledge/            port KnowledgeBase + implementasi (in-memory/fixture)
pipelines/            kurasi data (news: dedup → scoring → KB)
observability/        structlog + metrics registry (run_id per analisis)
app/                  composition root + CLI
```

Prinsip yang dijaga oleh struktur ini:

- **AI tidak pernah membaca data mentah.** Analis hanya menerima record
  terkurasi dari `KnowledgeBase`; kurasi terjadi di `pipelines/`.
- **Reasoning dibatasi rule engine.** Komite mengusulkan, `DecisionEngine`
  memutuskan; setiap override tercatat untuk audit.
- **Evidence wajib.** Skema memaksa setiap opini dan argumen membawa
  `EvidenceRef`; laporan akhir dapat direkonstruksi penuh dari audit trail.
- **Modular.** Menambah interface (web/API) atau mengganti analis heuristik
  dengan analis LLM adalah perubahan wiring di `app/container.py`, bukan
  perubahan core.

## Pengembangan

- Python ≥ 3.11 · [uv](https://docs.astral.sh/uv/) · ruff · mypy (strict) · pytest
- `make format` sebelum commit; CI menjalankan `make check`.
- Fixture demo: `data/fixtures/idx_demo.json` (parameter skenario; series harga
  disintesis deterministik oleh `knowledge/fixtures.py`).

## Disclaimer

Alat riset & edukasi. Output bukan nasihat investasi dan bukan ajakan
membeli/menjual efek. Keputusan investasi sepenuhnya tanggung jawab pengguna.
