# Memory Architecture

**Fase:** 2 — AI Architecture · **Status:** Draft v0.1

## 1. Jenis Memori

| Jenis | Isi | Umur |
|-------|-----|------|
| **Working memory** | State analisis berjalan (AnalysisState) | Per-run |
| **Short-term** | Konteks percakapan pengguna di Telegram | Sesi/beberapa hari |
| **Long-term factual** | Knowledge base (evidence terkurasi) | Persisten |
| **Episodic** | Riwayat rekomendasi & hasilnya (untuk evaluasi/learning) | Persisten |
| **User memory** | Watchlist, preferensi, gaya (persona) | Persisten per user |

## 2. Alur

- Working memory hidup di dalam graph state (checkpointed).
- Short-term percakapan disimpan ringkas + rangkuman untuk hemat token.
- Episodic memory mencatat: input, evidence, keputusan, confidence, lalu **outcome** aktual → dipakai backtesting & continuous learning.

## 3. Prinsip

- **Pisahkan fakta (KB) dari memori percakapan.** Fakta selalu dari KB; percakapan hanya untuk konteks interaksi.
- **Tidak menyimpan PII berlebih.** Simpan minimal yang diperlukan (lihat Security).
- **Traceability**: setiap rekomendasi tertaut ke evidence & versi prompt/model.

## 4. Retensi & Privasi

- Kebijakan retensi per jenis memori.
- Hak pengguna: hapus data pribadi & watchlist.

> TODO: Tetapkan store teknis untuk tiap jenis memori (Redis/Postgres/Vector DB) & kebijakan retensi.
