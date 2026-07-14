# Milestones

**Fase:** 6 — Delivery · **Status:** Draft v0.1

## Milestone Kunci (indikatif, isi tanggal nyata)

| ID | Milestone | Kriteria Selesai |
|----|-----------|------------------|
| M0 | Fondasi siap | Core skeleton, DB/vector, event bus, CI dasar berjalan |
| M1 | Pipeline data dasar | Market & news pipeline → KB, terjadwal |
| M2 | Market Brief harian | Brief otomatis pra-market dengan confidence |
| M3 | Analisis emiten | `/analyze` mengembalikan keputusan + evidence + reasoning |
| M4 | Decision & Confidence | Rule engine + confidence terkalibrasi aktif |
| M5 | Explainability lengkap | Audit trail + template output final |
| M6 | Evaluation gate | Regression AI di CI sebelum promote |
| M7 | Beta rilis | Pengguna beta memakai bot; feedback loop aktif |
| M8 | Alert event-driven | Notifikasi watchlist berjalan |
| M9 | Backtesting & HITL | Kalibrasi dari outcome + review manusia |
| M10 | Interface kedua | Dashboard web/API di atas core sama |

## Dependensi

- M2–M5 bergantung pada M0–M1.
- M9 bergantung pada akumulasi outcome (butuh waktu berjalan).

> TODO: Tetapkan tanggal, owner, & definisi "done" terukur per milestone.
