# Data Source Catalog

**Fase:** 3 — Data Platform · **Status:** Draft v0.1

Katalog seluruh sumber data, tipe, frekuensi, dan catatan legal. **Prinsip: AI tidak pernah membaca sumber mentah — semua lewat pipeline.**

## 1. Kategori Sumber

| Kategori | Contoh isi | Frekuensi | Catatan |
|----------|-----------|-----------|---------|
| Market data | Harga, volume, OHLC, indeks (IHSG/LQ45) | Intraday/EOD | Verifikasi lisensi penyedia |
| Foreign flow | Net foreign buy/sell | Harian | Penting untuk big-cap |
| Fundamental | Laporan keuangan, rasio, aksi korporasi | Kuartalan/event | Sumber resmi emiten/BEI |
| News | Media ekonomi Indonesia | Realtime/batch | Hormati ToS & hak cipta |
| Social | Cuitan/mention (mis. Twitter/X, forum) | Realtime | Perlu filter spam/bot |
| Macro | BI Rate, USDIDR, komoditas (batu bara, nikel, CPO, emas) | Harian/event | Sumber resmi/terpercaya |
| Domain KB | Peta emiten↔sektor, glosarium, rules | Statis/kurasi | Dibuat manual |

## 2. Metadata Wajib per Sumber

- `source_id`, `nama`, `tipe`, `metode akses (API/crawl)`, `frekuensi`, `lisensi/ToS`, `SLA/keandalan`, `PII?`.

## 3. Kepatuhan & Legal

- Patuhi Terms of Service & hak cipta tiap sumber.
- Simpan **ringkasan/olahan**, bukan reproduksi penuh konten berhak cipta.
- Catat basis legal pemakaian tiap sumber.

## 4. Kualitas Data

- Skor keandalan sumber; sumber tak kredibel di-*downrank* atau dibuang.
- Deduplikasi lintas sumber.

> TODO: Isi daftar penyedia konkret + status lisensi + fallback tiap kategori.
