# Changelog

Semua perubahan penting pada proyek ini dicatat di sini.
Format mengikuti [Keep a Changelog](https://keepachangelog.com/id/1.1.0/),
dan versi mengikuti [Semantic Versioning](https://semver.org/lang/id/).

## [0.2.0] — 2026-07-19

Gelombang pasca-MVP: lima fitur fase-2, semuanya lolos gerbang CI yang sama.

### Ditambahkan

- **Analis berita LLM** (opt-in `INVOS_LLM_ANALYSTS`) — kursi berita komite
  dapat diisi LLM yang menalar atas berita terkurasi; jawaban wajib JSON
  ketat dengan sitasi terbatas pada ref_id yang diberikan. Sitasi
  halusinasi, nilai di luar rentang, atau kegagalan penyedia jatuh kembali
  utuh ke analis leksikon deterministik. Versi provider/model tercatat
  pada tiap opini untuk audit.
- **Outcome tracking otomatis** — `OutcomeTracker` merekam return
  terealisasi (horizon dihitung dalam bar bursa, konsisten dengan
  backtester) secara idempoten; berjalan harian pasca-market di scheduler
  bot dan manual via `investment-os record-outcomes`. Kalibrasi confidence
  kini mengisi dirinya sendiri.
- **Alert event teknikal** — sweep watchlist mendeteksi harga menembus
  SMA-50, RSI-14 jenuh beli/jual, dan arus asing tak biasa (|z| ≥ 2).
  Kondisi berkelanjutan hanya dialert sekali sampai kondisi bersih
  (set event dipersist, skema v5).
- **Dashboard web internal** — `GET /` di `serve-api`: tile market brief,
  kalibrasi per-bucket, riwayat rekomendasi, dan analisis on-demand.
  Satu halaman mandiri tanpa aset eksternal, sadar mode gelap/terang.

### Diubah

- **Runtime bot diperkeras untuk produksi** — SIGTERM/SIGINT memicu
  shutdown anggun (batalkan task, tutup klien HTTP dan SQLite); task yang
  crash menjatuhkan proses secara bersih agar Docker me-restart. Klien
  Telegram menghormati `retry_after` pada 429 dan berhenti me-retry error
  permanen; polling bertahan saat gangguan jaringan panjang namun cepat
  gagal pada token salah. Broadcast diberi pacing di bawah rate limit dan
  otomatis mencabut langganan chat yang memblokir bot.

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

[0.2.0]: https://github.com/mirecodex/ai-investment-os/releases/tag/v0.2.0
[0.1.0]: https://github.com/mirecodex/ai-investment-os/releases/tag/v0.1.0
