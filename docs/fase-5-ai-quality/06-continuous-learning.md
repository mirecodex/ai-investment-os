# Continuous Learning

**Fase:** 5 — AI Quality · **Status:** Draft v0.1

## 1. Tujuan

Sistem membaik seiring waktu dari outcome nyata & feedback — tanpa mengorbankan grounding/keandalan.

## 2. Sumber Pembelajaran

- **Outcomes**: hasil aktual rekomendasi (dari episodic memory) → kalibrasi confidence.
- **Feedback pengguna**: 👍/👎 & komentar.
- **Review HITL**: koreksi pakar → golden set & prompt.
- **Drift monitoring**: pergeseran distribusi data/pasar.

## 3. Mekanisme (aman)

- **Kalibrasi confidence** berkala dari outcome.
- **Perbaikan prompt/rule** berbasis kesalahan yang terdokumentasi (bukan asal ubah).
- **Perluasan golden set** dari kasus nyata.
- **Update domain KB** (peta emiten↔driver) saat pasar berubah.
- (Opsional lanjutan) fine-tuning komponen tertentu — hanya setelah evaluasi ketat.

## 4. Guardrail

- Semua perubahan lewat Evaluation Framework (regression gate) sebelum rilis.
- Versi prompt/model dicatat → bisa rollback.
- Hindari feedback loop bias (mis. hanya belajar dari periode bullish).

## 5. Kadensi

- Kalibrasi & review kualitas berkala; audit drift rutin.

> TODO: Tetapkan siklus retraining/kalibrasi & kriteria promote perubahan.
