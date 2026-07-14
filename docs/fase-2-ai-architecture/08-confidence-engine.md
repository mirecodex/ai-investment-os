# Confidence Engine

**Fase:** 2 — AI Architecture · **Status:** Draft v0.1

## 1. Tujuan

Menghasilkan skor **confidence** yang terkalibrasi untuk tiap Market Brief & rekomendasi, agar pengguna tahu seberapa yakin sistem.

## 2. Faktor Penyusun Confidence

| Faktor | Kontribusi |
|--------|-----------|
| Kekuatan & kuantitas evidence | Lebih banyak evidence kredibel → confidence naik |
| Kesegaran data | Data basi → confidence turun |
| Konvergensi analis | Analis sepakat → naik; berselisih → turun |
| Konflik rule | Terpicu rule konflik (mis. R1) → turun |
| Kualitas sumber | Sumber kredibel → naik |
| Historis akurasi | Kalibrasi dari episodic memory/backtesting |

## 3. Formula (konsep)

```
confidence = calibrate(
    w1*evidence_strength +
    w2*freshness +
    w3*analyst_agreement -
    w4*rule_conflict +
    w5*source_quality
)
```
Bobot `w*` dikalibrasi terhadap hasil aktual (bukan ditebak). Output dipetakan ke rentang 0–100%.

## 4. Kalibrasi

- Gunakan riwayat: bandingkan confidence dengan outcome nyata (reliability diagram).
- Hindari *overconfidence*: terapkan penalti saat sinyal berkonflik.

## 5. Penyajian

- Market Brief: "Market Sentiment: Bullish · Confidence 83%".
- Rekomendasi: confidence + caveat utama.
- Confidence rendah → dorong human review & bahasa lebih hati-hati.

> TODO: Kalibrasi bobot dengan data historis; definisikan ambang LOW/MED/HIGH.
