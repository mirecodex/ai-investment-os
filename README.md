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
| Analis deterministik: technical, fundamental, news, foreign flow, quant, macro, sector rotation | ✅ |
| Research Manager: routing analis per ketersediaan data + kuorum | ✅ |
| Bull/Bear case + konsensus komite | ✅ |
| Decision Engine (rule R1/R1b/R2/R3, override audit) | ✅ |
| Confidence Engine (evidence, freshness, agreement, kalibrasi) | ✅ |
| News pipeline (dedup, near-dup, reliability & importance scoring) | ✅ |
| Market Brief harian | ✅ |
| Telegram bot (long polling) | ✅ |
| Persistensi (SQLite): rekomendasi, evidence, rule trigger, outcome, watchlist | ✅ |
| Data live: harga EOD (Yahoo interim) + crawler RSS media Indonesia | ✅ `--live` |
| Scheduler WIB: brief harian otomatis (`/subscribe`) + refresh KB live | ✅ |
| Layer LLM multi-provider: narasi CIO + numeric guard + prompt registry | ✅ |
| Evaluation framework: golden set (regression gate CI) + kalibrasi/ECE | ✅ |
| Alert watchlist: sweep post-market, notifikasi hanya perubahan material | ✅ |
| Deployment: Docker + compose + healthcheck (build di CI) | ✅ |
| Interface kedua: REST API internal (FastAPI) di atas core yang sama | ✅ |
| Foreign flow & fundamental live, provider berlisensi | ⬜ butuh keputusan provider |
| Analis LLM penuh (per-role), Postgres/vector store | ⬜ port sudah tersedia |

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
uv run investment-os history        # riwayat rekomendasi tersimpan (SQLite di var/)
uv run investment-os eval           # golden regression suite (juga jalan di CI)
uv run investment-os calibration    # hit rate arah + ECE dari outcome tersimpan
```

Mode live (harga EOD via Yahoo Finance + berita RSS, universe di
`data/universe/lq45-demo.json`):

```bash
uv run investment-os --live brief
uv run investment-os --live analyze BBCA
```

Catatan mode live: sumber gratis tidak menyediakan foreign flow dan
fundamental — analis terkait otomatis mundur (recuse) dan komite berjalan
dengan analis yang datanya tersedia. Sentimen berita memakai lexicon interim
sampai news-intelligence berbasis LLM aktif.

### Narasi CIO berbasis LLM (opsional, multi-provider)

Set salah satu API key di `.env` (lihat `.env.example`) dan setiap analisis
mendapat paragraf "Pandangan CIO" yang ditulis LLM — dijaga oleh *numeric
guard* (angka yang tidak bersumber dari evidence → narasi ditolak) dan tidak
pernah mengubah keputusan komite:

```
ANTHROPIC_API_KEY / OPENAI_API_KEY / GOOGLE_API_KEY / XAI_API_KEY /
DEEPSEEK_API_KEY / DASHSCOPE_API_KEY / ZHIPU_API_KEY / MINIMAX_API_KEY /
OPENROUTER_API_KEY ...
```

Provider pertama yang punya key dipakai; paksa dengan `INVOS_LLM_PROVIDER`,
ganti model dengan `INVOS_LLM_MODEL`. Prompt tersimpan berversi di
`prompts/` dan versi prompt + model dicatat pada tiap rekomendasi. Untuk
Anthropic, pasang extra: `uv pip install -e ".[anthropic]"`. Kegagalan LLM
(kunci salah, provider down, guard menolak) selalu jatuh kembali ke output
deterministik.

Menjalankan bot Telegram (butuh token dari @BotFather):

```bash
cp .env.example .env                # isi INVOS_TELEGRAM_BOT_TOKEN
uv run investment-os serve-telegram          # fixture
uv run investment-os --live serve-telegram   # data nyata + refresh berkala
```

Proses bot menjalankan polling + scheduler dalam satu event loop:
Market Brief dikirim otomatis ke pelanggan `/subscribe` setiap hari bursa
pukul `INVOS_BRIEF_TIME_WIB` (default 07:30 WIB); sweep alert watchlist
berjalan post-market pukul `INVOS_ALERT_TIME_WIB` (default 17:15 WIB) dan
hanya mengirim notifikasi saat ada perubahan material (keputusan berubah
atau rule baru aktif — bukan drift confidence); pada mode live, knowledge
base di-rebuild tiap `INVOS_REFRESH_INTERVAL_MINUTES` (default 60) dan
di-hot-swap tanpa restart.

## Arsitektur

```
interfaces/telegram   adapter tipis: router → presenter → Bot API
interfaces/api        adapter tipis: REST internal (FastAPI)
        │
core/                 service (graph wiring) · agents · decision · confidence
                      explain · market_intel      ← tidak mengimpor interfaces
        │
knowledge/            port KnowledgeBase + implementasi (in-memory/fixture)
data/                 persistensi SQLite (rekomendasi, outcome, watchlist)
pipelines/            kurasi data (news: dedup → scoring → KB)
eval/                 golden suite runner + metrik kalibrasi (fase 5)
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

### REST API internal (interface kedua)

```bash
uv run investment-os serve-api --host 127.0.0.1 --port 8000
# GET  /health · /tickers · /brief · /recommendations · /calibration
# POST /analyze/{ticker}
# Dokumentasi interaktif: http://127.0.0.1:8000/docs
```

Adapter tipis di atas core yang sama dengan bot Telegram (prinsip
hexagonal terbukti: menambah interface tanpa menyentuh core). Ditujukan
untuk dashboard/integrasi internal — jalankan di belakang boundary
jaringan/auth Anda sendiri.

## Deployment (Docker)

```bash
cp .env.example .env             # isi INVOS_TELEGRAM_BOT_TOKEN (+ LLM key opsional)
make docker-up                   # build + jalankan bot (compose, restart otomatis)
make docker-logs
```

Image berjalan non-root dengan healthcheck bawaan (`investment-os health`);
SQLite hidup di volume `invos-var` sehingga rekomendasi, outcome, dan
watchlist selamat dari restart/upgrade. Aktifkan data nyata dengan
`INVOS_DATA_MODE=live` di compose/env. CI membangun image yang sama setelah
lint, typecheck, test, dan golden gate — sesuai pipeline
[docs/fase-4 deployment](docs/fase-4-engineering/08-deployment.md).

## Pengembangan

- Python ≥ 3.11 · [uv](https://docs.astral.sh/uv/) · ruff · mypy (strict) · pytest
- `make format` sebelum commit; CI menjalankan `make check`.
- Fixture demo: `data/fixtures/idx_demo.json` (parameter skenario; series harga
  disintesis deterministik oleh `knowledge/fixtures.py`).

## Disclaimer

Alat riset & edukasi. Output bukan nasihat investasi dan bukan ajakan
membeli/menjual efek. Keputusan investasi sepenuhnya tanggung jawab pengguna.
