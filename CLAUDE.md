# AI Investment OS — IDX Edition

AI investment research platform untuk bursa Indonesia. BUKAN trading bot:
tidak ada eksekusi order, setiap keluaran membawa disclaimer. Desain lengkap
(6 fase, 43 dokumen) di `docs/`; keputusan arsitektur di `docs/adr/`.

## Commands

```bash
make install          # uv venv + dev deps (Python >= 3.11)
make check            # ruff + mypy --strict + pytest — wajib hijau sebelum merge
make format           # ruff format
uv run investment-os eval          # golden regression gate — wajib 4/4 sebelum merge
uv run investment-os analyze BBCA  # smoke test offline (fixture)
uv run pytest tests/test_foo.py -q # satu file test
```

CI (`.github/workflows/ci.yml`) menjalankan lint, typecheck, test, golden
gate, lalu build image Docker — persis urutan `make check` + `eval`.

## Architecture (hexagonal — dilindungi struktur, jangan dilanggar)

```
interfaces/  (telegram, api+dashboard)  → adapter tipis, boleh impor core
core/        service · agents · decision · confidence · explain · alerts · outcomes
             TIDAK PERNAH mengimpor interfaces/
knowledge/   port KnowledgeBase + in-memory/fixture/live/refreshable
data/        SQLite (migrasi forward-only di db.py MIGRATIONS — hanya append)
pipelines/   kurasi news/market + scheduler WIB
llm/         registry multi-provider + PromptStore (prompts/<nama>@vN.md)
eval/        golden suite · reliability/ECE · backtest point-in-time
app/         composition root (container.py) + CLI + runtime bot
```

Aturan inti:
- Analis hanya menerima data terkurasi dari `KnowledgeBase` — tidak pernah
  data mentah/web. Semua analis di belakang protocol `Analyst` (async).
- Komite mengusulkan; `DecisionEngine` (rules R1/R1b/R2/R3) memutuskan;
  setiap override tercatat di audit trail.
- LLM selalu di belakang port (`core/llm.py`), opt-in, dan wajib punya
  fallback deterministik. Keputusan komite tidak boleh bergantung pada
  ketersediaan LLM. Output LLM wajib tervalidasi (sitasi ⊆ evidence).
- Mengganti wiring = ubah `app/container.py`, bukan core.
- Golden suite (`eval/golden/decisions.json`) memaku keputusan; kalau
  perubahanmu mengubah hasil golden secara sengaja, pin ulang secara sadar
  dan jelaskan di commit — jangan pernah "menyesuaikan supaya lolos".

## Conventions

- Branch per fitur (`feature/...` / `chore/...`), merge ke `main` dengan
  `--no-ff`, push branch dan main.
- TANPA komentar header di atas file (tanpa docstring modul deskriptif).
  Komentar hanya untuk constraint yang tidak terlihat dari kode.
- Commit message: imperatif, ringkas, tanpa trailer atribusi apa pun.
- mypy strict untuk `src/` (tests tidak di-typecheck ketat).
- Teks yang dilihat pengguna (Telegram/CLI/dashboard) berbahasa Indonesia;
  identifier dan log berbahasa Inggris.
- File sementara/scratch jangan di-commit; `var/` (SQLite lokal) sudah
  di-gitignore.

## Gotchas

- `pipelines/scheduler.py` WIB = UTC+7; `DailyAt` default hanya hari kerja.
- Horizon outcome/backtest dihitung dalam BAR BURSA, bukan hari kalender.
- `NEUTRAL_BAND` di committee: opini netral tidak ikut memberi suara arah
  (tapi tetap dihitung untuk agreement) — jangan "diperbaiki".
- Fixture (`data/fixtures/idx_demo.json`) berisi parameter skenario;
  series harga disintesis deterministik oleh `knowledge/fixtures.py`.
- Mode live pakai sumber gratis: tanpa foreign flow & fundamental — analis
  terkait recuse otomatis; ini perilaku yang diharapkan.
