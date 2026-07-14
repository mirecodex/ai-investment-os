# Backtesting

**Fase:** 5 — AI Quality · **Status:** Draft v0.1

## 1. Tujuan

Menguji seberapa baik rekomendasi historis akan berjalan — untuk kalibrasi confidence & evaluasi arah, **bukan** klaim profit.

## 2. Prinsip

- **Point-in-time correctness**: gunakan hanya data yang tersedia saat itu (hindari look-ahead bias).
- **Konteks makro** ikut dipertimbangkan (Market Brief historis).
- Fokus pada **direction accuracy** & kualitas reasoning, bukan menjanjikan return.

## 3. Metodologi

```
Untuk tiap kasus historis:
  bangun ulang state (evidence, market brief) pada tanggal T
  jalankan pipeline → keputusan + confidence
  ukur outcome pada horizon H (mis. 1w/1m) → simpan ke outcomes
```

## 4. Metrik

- Hit rate arah (BUY benar naik, SELL benar turun) pada horizon tertentu.
- Kalibrasi: confidence tinggi seharusnya lebih akurat.
- Analisis kesalahan: kapan sistem salah & kenapa.

## 5. Batasan & Kejujuran

- Backtest bukan jaminan performa masa depan.
- Waspadai overfitting terhadap periode tertentu.
- Sajikan hasil apa adanya (termasuk kelemahan).

> TODO: Definisikan horizon, benchmark (mis. IHSG), & prosedur point-in-time.
