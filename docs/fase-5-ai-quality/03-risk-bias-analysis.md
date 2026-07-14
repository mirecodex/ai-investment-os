# Risk & Bias Analysis

**Fase:** 5 — AI Quality · **Status:** Draft v0.1

## 1. Tujuan

Mengidentifikasi & memitigasi risiko dan bias yang bisa merusak kualitas/kepercayaan.

## 2. Risiko Model/AI

| Risiko | Mitigasi |
|--------|----------|
| Hallucination | Evidence gating, grounding, self-check (dok terpisah) |
| Overconfidence | Confidence Engine terkalibrasi + rule floor |
| Data poisoning (sosial) | Spam/bot detection, bobot rendah untuk sosial |
| Recency bias | Time-aware retrieval + konteks fundamental |
| Herding/pom-pom | Sosial bukan penentu; utamakan fundamental/flow |

## 3. Risiko Domain/Pasar

- Perubahan kebijakan mendadak (regulasi, larangan ekspor).
- Likuiditas rendah pada emiten kecil → sinyal kurang andal.
- Aksi korporasi mengubah fundamental (dilusi, dsb.).

## 4. Bias yang Diwaspadai

- Bias sumber (media condong), bias sektor, bias big-cap.
- Bias periode (backtest pada rezim pasar tertentu).

## 5. Risiko Produk/Etika

- Pengguna salah mengira ini nasihat investasi → disclaimer tegas & bahasa hati-hati.
- Tidak menjanjikan profit; hindari FOMO/pump.

> TODO: Susun risk register dengan pemilik & tingkat keparahan.
