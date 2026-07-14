# Folder Structure

**Fase:** 6 — Delivery · **Status:** Draft v0.1

Struktur usulan yang mencerminkan pemisahan **core vs interface vs pipeline** (modular).

```
ai-investment-os/
├── core/                     # domain & orchestration (bebas dari interface)
│   ├── agents/               # analis, bull/bear, committee, cio
│   ├── graph/                # LangGraph workflow & state
│   ├── decision/             # rule engine
│   ├── confidence/           # confidence engine
│   ├── explain/              # explainability engine
│   └── market_intel/         # market brief builder
├── pipelines/                # data platform
│   ├── market/
│   ├── news/
│   ├── social/
│   ├── fundamental/
│   └── scheduler/
├── knowledge/                # RAG & KB (retrieval, embedding, schema)
├── interfaces/               # adapters tipis
│   ├── telegram/
│   ├── api/                  # (nanti) public/internal API
│   └── web/                  # (nanti) dashboard
├── data/                     # akses DB, vector, cache, models
├── eval/                     # evaluation framework, golden set, backtesting
├── prompts/                  # prompt registry (berversi)
├── infra/                    # IaC, deployment, config
├── observability/            # logging, tracing, metrics
├── tests/
└── docs/                     # dokumentasi (fase 1–6)
```

## Prinsip

- `core/` tidak boleh mengimpor `interfaces/`.
- Menambah interface/market = menambah folder adapter, bukan mengubah core.
- `prompts/` & `eval/` sekelas warga utama (bukan afterthought).

> TODO: Sesuaikan dengan bahasa/framework terpilih.
