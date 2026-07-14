# ADR 0001 — Graph runtime sendiri untuk workflow komite (bukan LangGraph, untuk saat ini)

**Status:** Accepted · 2026-07-14

## Konteks

Dokumen fase 2 memodelkan Investment Committee sebagai graph (node = step,
edge kondisional, state bersama) dan menyebut LangGraph sebagai contoh.
Pada Tahap 0 seluruh analis masih deterministik (belum ada panggilan LLM),
dan pemilihan provider LLM masih terbuka (TODO di dokumen desain).

## Keputusan

Implementasikan runtime graph minimal sendiri (`core/graph/runtime.py`,
±150 baris): node async yang mengembalikan patch state, edge kondisional,
timeout & kebijakan error per node, audit trail otomatis.

## Konsekuensi

- Nol dependensi orkestrasi; committee dapat diuji unit tanpa LLM.
- API sengaja dibuat seukuran/seselaras LangGraph (state + patch + conditional
  edges), sehingga migrasi nanti berupa penggantian runtime di
  `AnalysisService._build_graph`, bukan penulisan ulang node.
- Fitur LangGraph yang belum dibutuhkan (checkpoint persisten, streaming,
  human-in-the-loop interrupt) menjadi pemicu evaluasi ulang ADR ini —
  kemungkinan besar saat analis LLM pertama masuk.
