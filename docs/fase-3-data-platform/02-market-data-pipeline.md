# Market Data Pipeline

**Fase:** 3 — Data Platform · **Status:** Draft v0.1

## 1. Tujuan

Menyediakan harga, volume, indeks, foreign flow, dan data makro dalam bentuk terstruktur & tepat waktu untuk Market Brief dan analis (Technical/Quant/Foreign Flow/Macro).

## 2. Alur

```
Provider/API → Ingest → Validate → Normalize → Store(TS DB) → Feature/Aggregate → KB(market/macro)
```

## 3. Komponen

- **Ingest**: penarikan intraday/EOD sesuai jadwal bursa.
- **Validate**: cek gap, outlier, corporate action adjustment.
- **Normalize**: format ticker, timezone (WIB), satuan.
- **Aggregate**: hitung indikator (MA, RSI, volatilitas), agregasi sektor, net foreign flow.
- **Publish**: tulis ke time-series store + snapshot ke KB.

## 4. Data untuk Market Brief

Setiap pra-market, pipeline menyiapkan angka Market Brief: IHSG %, foreign flow, sektor kuat/lemah, komoditas (coal/nickel/CPO/gold), USDIDR, status BI Rate.

## 5. Kualitas & Keandalan

- Corporate action handling (split, dividen) agar harga historis konsisten.
- Fallback provider bila sumber utama gagal.
- Monitoring keterlambatan/gap data.

> TODO: Pilih provider market data & TS DB; definisikan skema tabel harga/flow.
