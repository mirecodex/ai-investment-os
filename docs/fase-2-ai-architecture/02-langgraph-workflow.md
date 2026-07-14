# LangGraph Workflow

**Fase:** 2 — AI Architecture · **Status:** Draft v0.1

## 1. Kenapa Graph

Investment Committee adalah alur ber-tahap dengan percabangan kondisional & konvergensi. Model *graph* (mis. LangGraph) cocok: node = agent/step, edge = alur, state = konteks bersama.

## 2. Struktur State (bersama antar node)

```
AnalysisState:
  ticker: str
  market_brief: MarketBrief        # konteks market harian
  raw_evidence: dict[source -> list]
  analyst_outputs: dict[role -> AnalystOpinion]
  bull_case: Argument
  bear_case: Argument
  committee_notes: list
  decision: Decision               # BUY/HOLD/SELL + reason
  confidence: float
  audit_trail: list                # untuk explainability
```

## 3. Node Utama

1. `load_context` — ambil Market Brief + data emiten dari knowledge base.
2. `route_analysts` — Research Manager memilih analis relevan.
3. `run_analysts` (paralel) — tiap analis mengisi `analyst_outputs`.
4. `build_bull` / `build_bear`.
5. `committee_review` — konsolidasi + cek konsistensi.
6. `apply_rules` — Decision Engine (rule + evidence gating).
7. `cio_decision` — keputusan akhir + confidence.
8. `explain` — susun reasoning & audit trail.
9. `deliver` — format ke Telegram.

## 4. Percabangan Kondisional

- Jika evidence tidak cukup → node `insufficient_evidence` → output HOLD/abstain.
- Jika rule terpicu (mis. foreign sell besar + berita negatif) → override ke HOLD.
- Jika confidence < ambang → tandai "low confidence" & sarankan human review.

## 5. Ketahanan

- **Checkpointing** state agar bisa retry per node.
- **Timeout & fallback** per node (mis. satu analis gagal → lanjut dengan catatan).
- **Idempotency** untuk event-driven runs.

> TODO: Diagram graph final + definisi kondisi edge secara eksplisit.
