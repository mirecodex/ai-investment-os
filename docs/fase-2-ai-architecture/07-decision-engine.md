# Decision Engine

**Fase:** 2 — AI Architecture · **Status:** Draft v0.1

## 1. Peran

LLM menalar, tetapi **keputusan akhir dibatasi rule engine + evidence**. Decision Engine mencegah rekomendasi impulsif dan menjaga konsistensi.

## 2. Prinsip Inti

> LLM = reasoning. Decision Engine = guardrail keputusan.

Keputusan (BUY/HOLD/SELL) hanya sah jika lolos evidence gating **dan** tidak melanggar business rules.

## 3. Contoh Reasoning Rules

```
RULE R1 (Sentimen vs Fundamental):
  IF fundamental = STRONG
  AND news_sentiment = NEGATIVE
  AND foreign_flow = HEAVY_SELL
  THEN keputusan := HOLD
  REASON := "Fundamental kuat, tetapi sentimen pasar masih negatif."

RULE R2 (Evidence gating):
  IF evidence_count < min_threshold OR data_stale
  THEN keputusan := HOLD/ABSTAIN
  REASON := "Bukti tidak memadai."

RULE R3 (Confidence floor):
  IF confidence < 0.6
  THEN tandai LOW_CONFIDENCE + sarankan human review.

RULE R4 (No guarantee):
  Dilarang menyatakan jaminan profit / kepastian arah.
```

## 4. Arsitektur

- **Rule store** deklaratif (mudah diaudit & diubah tanpa retrain).
- **Evaluator** menjalankan rule atas output committee + evidence.
- **Override log**: setiap kali rule mengubah keputusan LLM, dicatat untuk audit.

## 5. Prioritas

Rule engine berada **setelah** committee dan **sebelum** CIO final, atau sebagai constraint pada CIO. Rule bersifat *hard constraint* — tidak bisa ditimpa LLM.

> TODO: Susun katalog rule lengkap bersama pakar domain + ambang batas.
