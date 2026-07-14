# Observability

**Fase:** 4 — Engineering · **Status:** Draft v0.1

## 1. Tujuan

Memahami kesehatan sistem **dan** kualitas AI. Untuk sistem LLM, observability mencakup jejak reasoning, biaya token, dan kualitas output.

## 2. Tiga Pilar + AI

- **Logs**: terstruktur, dengan `run_id`, `ticker`, `user_id` (ter-anonim bila perlu).
- **Metrics**: latency, error rate, throughput, biaya token/LLM, cache hit.
- **Traces**: alur per node graph (analis → committee → CIO).
- **AI observability**: prompt/response tersimpan (berversi), evidence dipakai, rule terpicu, confidence vs outcome.

## 3. Dashboard Kunci

- Latency & sukses analisis on-demand.
- Biaya LLM per hari/per fitur.
- Distribusi keputusan (BUY/HOLD/SELL) & confidence.
- Akurasi arah (dari backtesting/outcome).
- Kesehatan pipeline (keterlambatan/gap data).

## 4. Alerting Operasional

- Pipeline data telat/gagal.
- Lonjakan error/biaya.
- Provider LLM/data down → aktifkan fallback.

## 5. Audit

Setiap rekomendasi dapat direkonstruksi penuh (audit trail) untuk kepercayaan & debugging.

> TODO: Pilih stack observability (mis. OpenTelemetry) & definisi SLI/SLO.
