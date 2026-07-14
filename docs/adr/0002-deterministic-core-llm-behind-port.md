# ADR 0002 — Core deterministik dulu; LLM & data provider di belakang port

**Status:** Accepted · 2026-07-14

## Konteks

Dua keputusan besar masih terbuka di dokumen desain: provider LLM (fase 4,
cost estimation) dan penyedia data berlisensi (fase 3, data source catalog).
Menunggu keduanya berarti tidak ada fondasi yang bisa diverifikasi; menebak
keduanya berarti rework.

## Keputusan

1. Semua analis mengimplementasikan protocol `Analyst` dengan skema output
   tervalidasi (`AnalystOpinion` + `EvidenceRef` wajib). Implementasi Tahap 0
   bersifat heuristik-deterministik (indikator teknikal, rasio fundamental,
   sentimen berita terbobot, z-score foreign flow).
2. Akses data hanya lewat protocol `KnowledgeBase`; implementasi Tahap 0
   adalah in-memory store yang diisi fixture + news pipeline.
3. Decision Engine, Confidence Engine, explainability, dan graph runtime —
   bagian yang memang harus deterministik selamanya — dibangun penuh sekarang
   dan diuji unit.

## Konsekuensi

- `make check` dan seluruh alur `/analyze` berjalan offline & reproducible;
  regresi logika keputusan terdeteksi tanpa biaya token.
- Mengaktifkan analis LLM = implementasi baru protocol `Analyst` + wiring di
  `app/container.py`. Skema output dan evidence gating tidak berubah, sehingga
  guardrail (rule engine) langsung berlaku untuk output LLM.
- Angka-angka heuristik (bobot, ambang) adalah placeholder terdokumentasi,
  bukan hasil kalibrasi — kalibrasi menunggu backtesting (fase 5).
