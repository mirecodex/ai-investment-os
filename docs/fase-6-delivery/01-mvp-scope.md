# MVP Scope

**Fase:** 6 — Delivery · **Status:** Draft v0.1

## 1. Tujuan MVP

Membuktikan nilai inti: **Market Brief harian + analisis emiten ber-reasoning** untuk IDX lewat Telegram, dengan fondasi modular yang siap dikembangkan.

## 2. In Scope (MVP)

- **Market**: IDX, fokus ~30–50 emiten likuid (basis LQ45).
- **Interface**: Telegram bot.
- **Fitur**: Market Brief harian, `/analyze <ticker>`, watchlist dasar, explainability, confidence.
- **AI**: Investment Committee inti (subset analis relevan) + Decision Engine (rule dasar) + Confidence + Explainability.
- **Data**: market data, foreign flow, news pipeline, fundamental dasar, social (bobot rendah).

## 3. Out of Scope (MVP)

- Market selain IDX; dashboard web; API publik; eksekusi order; simulasi portfolio penuh; fine-tuning.

## 4. Definisi Sukses

- Market Brief harian konsisten & tepat waktu.
- Analisis on-demand ber-evidence & ber-alasan.
- Pengguna beta menilai output "berguna" (lihat North Star).
- Fondasi modular terbukti (menambah analis/emiten tanpa rewrite).

## 5. Prinsip

"Fondasi benar dulu, fitur menyusul." MVP mengaktifkan subset fitur di atas arsitektur penuh, bukan membangun prototipe buang.

> TODO: Kunci daftar emiten MVP + subset analis yang diaktifkan.
