# Changelog

Semua perubahan penting pada proyek ini dicatat di sini.
Format mengikuti [Keep a Changelog](https://keepachangelog.com/id/1.1.0/),
dan versi mengikuti [Semantic Versioning](https://semver.org/lang/id/).

## [0.1.0] — 2026-07-14

Rilis pertama, dipotong dari commit pertama yang lolos seluruh gerbang CI:
ruff lint, mypy strict, 115 pengujian, golden regression suite (4/4), dan
build image kontainer.

### Ditambahkan

- **Komite analis deterministik** — 7 analis (teknikal, fundamental,
  sentimen berita, arus asing, kuantitatif, makro, rotasi sektor) yang
  dirutekan research manager dengan kuorum; konsensus memakai pita netral
  agar opini netral tidak menyeret arah.
- **Decision engine deklaratif** — aturan konflik (R1/R1b), gerbang bukti
  (R2), dan lantai keyakinan (R3) dengan jejak audit override lengkap.
- **Confidence engine** — kekuatan bukti tersaturasi, peluruhan kesegaran,
  dispersi kesepakatan, penalti konflik aturan, dan hook kalibrasi;
  pita LOW/MEDIUM/HIGH.
- **Dua antarmuka** — bot Telegram (langganan, alert, brief harian WIB)
  dan REST API internal (FastAPI).
- **Persistensi** — SQLite dengan migrasi forward-only v1–v4
  (rekomendasi, langganan, status alert).
- **Lapisan naratif LLM di belakang port** — 12 penyedia dipilih lewat
  env key natif; inti deterministik tidak pernah bergantung padanya.
  Narasi dijaga guard numerik (tanpa angka tak bersumber, tanpa frasa
  jaminan).
- **Pipeline data live** — Yahoo chart API + crawler RSS dengan leksikon
  sentimen bahasa Indonesia dan filter near-duplicate; scheduler WIB
  (hari bursa saja) dengan knowledge base hot-swap.
- **Evaluasi** — golden suite sebagai gerbang regresi CI, laporan
  reliabilitas per-bucket + ECE, dan backtesting point-in-time tanpa
  look-ahead (`investment-os backtest`).
- **Operasional** — image Docker multi-stage non-root dengan healthcheck,
  docker-compose, Makefile, CI GitHub Actions (aksi milik GitHub saja).

### Tidak termasuk (by design)

- Eksekusi order. Ini alat riset dan pendukung keputusan, bukan bot
  auto-trading; setiap keluaran menyertakan disclaimer.

[0.1.0]: https://github.com/mirecodex/ai-investment-os/releases/tag/v0.1.0
