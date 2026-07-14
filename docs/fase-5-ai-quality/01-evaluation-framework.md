# Evaluation Framework

**Fase:** 5 — AI Quality · **Status:** Draft v0.1

## 1. Tujuan

Mengukur kualitas AI secara sistematis sebelum & sesudah rilis. Perubahan prompt/model/rule harus lulus evaluasi (regression gate).

## 2. Dimensi yang Dievaluasi

| Dimensi | Pertanyaan |
|---------|-----------|
| Groundedness | Apakah klaim didukung evidence? |
| Faithfulness | Apakah reasoning konsisten dengan evidence & rule? |
| Direction accuracy | Apakah arah rekomendasi benar (via outcome/backtest)? |
| Calibration | Apakah confidence sesuai realitas? |
| Explainability | Apakah alasan jelas & dapat ditelusuri? |
| Safety | Apakah menghindari jaminan profit & mengikuti disclaimer? |

## 3. Metode

- **Golden set**: kumpulan kasus emiten+konteks dengan penilaian pakar sebagai acuan.
- **LLM-as-judge** (dengan hati-hati) + review manusia untuk kasus sensitif.
- **Automated checks**: setiap klaim punya evidence? rule dijalankan benar? output schema valid?
- **Regression suite**: dijalankan di CI sebelum promote.

## 4. Metrik

- % klaim ber-evidence, direction accuracy, calibration error (mis. ECE), pelanggaran safety = 0 target.

## 5. Kadensi

- Pra-rilis: wajib lulus regression.
- Berkala: evaluasi drift kualitas seiring perubahan pasar/data.

> TODO: Bangun golden set awal + definisikan ambang lulus per metrik.
