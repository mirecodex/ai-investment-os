# Prompt Engineering Guide

**Fase:** 2 — AI Architecture · **Status:** Draft v0.1

## 1. Prinsip

1. **Grounding wajib** — agent hanya boleh menalar dari evidence yang diberikan; dilarang mengarang fakta/angka.
2. **Structured output** — semua agent mengembalikan schema baku (JSON) agar dapat divalidasi.
3. **Evidence-first** — setiap klaim menyertakan referensi evidence.
4. **Konteks lokal** — sistem prompt memuat konteks IDX & Market Brief.
5. **Kalibrasi** — minta confidence eksplisit + caveat.

## 2. Struktur Prompt (template)

```
[SYSTEM]
Kamu adalah {role} pada AI Investment Committee untuk pasar saham Indonesia (IDX).
Aturan: hanya menalar dari EVIDENCE. Dilarang mengarang angka. Jika data kurang,
katakan tidak cukup bukti. Keluarkan JSON sesuai SCHEMA.

[CONTEXT]
Market Brief: {market_brief}
Emiten: {ticker_profile}

[EVIDENCE]
{curated_evidence}

[TASK]
Analisis dari sudut {role}. Kembalikan AnalystOpinion (JSON).

[SCHEMA]
{json_schema}
```

## 3. Teknik

- **Few-shot** contoh reasoning lokal (mis. "CPO naik → sawit").
- **Guardrail** anti-hallucination (lihat dok Hallucination Prevention).
- **Self-check**: minta agent memverifikasi tiap klaim punya evidence sebelum menutup.
- **Refusal**: jika diminta "jaminan profit" → tolak, kembalikan disclaimer.

## 4. Versi & Uji

- Prompt disimpan sebagai artefak berversi (prompt registry).
- Setiap perubahan prompt diuji lewat Evaluation Framework sebelum rilis.

> TODO: Lampirkan prompt final per agent + contoh few-shot berbahasa Indonesia.
