# Backend Architecture

**Fase:** 4 — Engineering · **Status:** Draft v0.1

## 1. Prinsip

**Core engine terpisah dari interface.** Telegram hanya salah satu adapter. Core yang sama nantinya melayani dashboard web, API, alert, dan simulasi portfolio.

## 2. Lapisan

```
Interfaces:   Telegram Bot | (nanti) Web | (nanti) Public API
      │
Application:  Orchestration (LangGraph), Decision Engine, Confidence,
              Explainability, Market Intelligence Layer
      │
Domain:       Agents, Rules, Investment logic
      │
Data:         Pipelines, Knowledge Base (RAG), DB, Cache
      │
External:     LLM provider, Data providers, Message broker
```

## 3. Modularitas

- Setiap interface = adapter tipis yang memanggil core services.
- Market adapter (IDX) terisolasi → menambah market lain = adapter baru, bukan rewrite.
- Pipelines sebagai service independen di belakang event bus.

## 4. Pola

- **Ports & adapters (hexagonal)** untuk isolasi core dari I/O.
- **Async** untuk pipeline & pemanggilan LLM paralel.
- **Job queue** untuk beban berat (analisis multi-agent).

## 5. Ketahanan

- Timeout & retry pada pemanggilan LLM/data.
- Circuit breaker untuk provider eksternal.
- Graceful degradation (mis. satu analis gagal → lanjut dengan catatan).

> TODO: Pilih bahasa/framework backend & definisikan batas service.
