# AI Investment OS — IDX Edition

> **AI Investment Research Platform untuk Pasar Saham Indonesia (Bursa Efek Indonesia / IDX)**
> Antarmuka pertama: Telegram · Platform pengguna utama: Stockbit · Bahasa: Indonesia

Ini **bukan** trading bot otomatis. Ini adalah *AI Investment Research Platform* — semacam "Bloomberg Terminal versi AI" yang berfokus penuh pada konteks Indonesia. Sistem mengumpulkan data, melakukan riset, menyusun *investment thesis*, mendebatkannya lewat sebuah *Investment Committee* multi-agent, menganalisis risiko, lalu memberikan rekomendasi **beserta alasannya**.

---

## Filosofi Desain

1. **Indonesia-first, bukan generik.** Sistem dioptimalkan untuk IDX, emiten Indonesia, makro Indonesia (BI Rate, Rupiah, harga komoditas: batu bara, nikel, CPO, emas), berita & sentimen berbahasa Indonesia, serta konteks regulasi OJK/BEI. Dukungan market lain (mis. US) ditambahkan belakangan lewat *adapter* baru, bukan dengan membangun ulang fondasi.
2. **Data selalu lewat pipeline, AI tidak pernah baca data mentah.** Setiap sumber (berita, sosial media, fundamental, market data) melewati tahap crawl → clean → summarize → extract → mapping → scoring → sentiment → knowledge base sebelum menyentuh agent.
3. **Konteks dulu, baru analisis saham.** Ada *Market Intelligence Layer* yang membuat **Market Brief** harian; semua analisis saham berjalan di atas konteks market hari itu.
4. **Reasoning dibatasi rule engine.** LLM bertugas menalar, tetapi keputusan akhir dibatasi *business rules* + *evidence*. Contoh: fundamental kuat tetapi berita jelek + foreign sell besar → sistem tidak boleh langsung BUY, wajib HOLD dengan alasan.
5. **Modular sejak awal.** Core engine dipisah dari antarmuka. Telegram hanya interface pertama; core yang sama nantinya melayani dashboard web, API internal, alert otomatis, dan simulasi portfolio.

---

## Peta Dokumentasi (6 Fase · 43 Dokumen)

### Fase 1 — Product & Research
| # | Dokumen |
|---|---------|
| 1 | [Vision & Product Strategy](fase-1-product-research/01-vision-product-strategy.md) |
| 2 | [Product Requirements Document (PRD)](fase-1-product-research/02-product-requirements-document.md) |
| 3 | [Domain Research — Pasar Modal Indonesia](fase-1-product-research/03-domain-research-pasar-modal-indonesia.md) |
| 4 | [Competitive Analysis](fase-1-product-research/04-competitive-analysis.md) |
| 5 | [Stakeholder & User Persona](fase-1-product-research/05-stakeholder-user-persona.md) |

### Fase 2 — AI Architecture
| # | Dokumen |
|---|---------|
| 1 | [Multi-Agent Architecture](fase-2-ai-architecture/01-multi-agent-architecture.md) |
| 2 | [LangGraph Workflow](fase-2-ai-architecture/02-langgraph-workflow.md) |
| 3 | [Agent Specifications](fase-2-ai-architecture/03-agent-specifications.md) |
| 4 | [Prompt Engineering Guide](fase-2-ai-architecture/04-prompt-engineering-guide.md) |
| 5 | [RAG & Knowledge Base Design](fase-2-ai-architecture/05-rag-knowledge-base-design.md) |
| 6 | [Memory Architecture](fase-2-ai-architecture/06-memory-architecture.md) |
| 7 | [Decision Engine](fase-2-ai-architecture/07-decision-engine.md) |
| 8 | [Confidence Engine](fase-2-ai-architecture/08-confidence-engine.md) |
| 9 | [Explainability Engine](fase-2-ai-architecture/09-explainability-engine.md) |

### Fase 3 — Data Platform
| # | Dokumen |
|---|---------|
| 1 | [Data Source Catalog](fase-3-data-platform/01-data-source-catalog.md) |
| 2 | [Market Data Pipeline](fase-3-data-platform/02-market-data-pipeline.md) |
| 3 | [News Intelligence Pipeline](fase-3-data-platform/03-news-intelligence-pipeline.md) |
| 4 | [Social Intelligence Pipeline](fase-3-data-platform/04-social-intelligence-pipeline.md) |
| 5 | [Fundamental Pipeline](fase-3-data-platform/05-fundamental-pipeline.md) |
| 6 | [Scheduler & Event Processing](fase-3-data-platform/06-scheduler-event-processing.md) |
| 7 | [Database & Vector Schema](fase-3-data-platform/07-database-vector-schema.md) |

### Fase 4 — Engineering
| # | Dokumen |
|---|---------|
| 1 | [Backend Architecture](fase-4-engineering/01-backend-architecture.md) |
| 2 | [API Design](fase-4-engineering/02-api-design.md) |
| 3 | [Telegram Bot UX](fase-4-engineering/03-telegram-bot-ux.md) |
| 4 | [Authentication](fase-4-engineering/04-authentication.md) |
| 5 | [Infrastructure](fase-4-engineering/05-infrastructure.md) |
| 6 | [Observability](fase-4-engineering/06-observability.md) |
| 7 | [Security](fase-4-engineering/07-security.md) |
| 8 | [Deployment](fase-4-engineering/08-deployment.md) |
| 9 | [Cost Estimation](fase-4-engineering/09-cost-estimation.md) |

### Fase 5 — AI Quality
| # | Dokumen |
|---|---------|
| 1 | [Evaluation Framework](fase-5-ai-quality/01-evaluation-framework.md) |
| 2 | [Backtesting](fase-5-ai-quality/02-backtesting.md) |
| 3 | [Risk & Bias Analysis](fase-5-ai-quality/03-risk-bias-analysis.md) |
| 4 | [Hallucination Prevention](fase-5-ai-quality/04-hallucination-prevention.md) |
| 5 | [Human-in-the-Loop](fase-5-ai-quality/05-human-in-the-loop.md) |
| 6 | [Continuous Learning](fase-5-ai-quality/06-continuous-learning.md) |

### Fase 6 — Delivery
| # | Dokumen |
|---|---------|
| 1 | [MVP Scope](fase-6-delivery/01-mvp-scope.md) |
| 2 | [Production Scope](fase-6-delivery/02-production-scope.md) |
| 3 | [Roadmap](fase-6-delivery/03-roadmap.md) |
| 4 | [Milestones](fase-6-delivery/04-milestones.md) |
| 5 | [Coding Standards](fase-6-delivery/05-coding-standards.md) |
| 6 | [Folder Structure](fase-6-delivery/06-folder-structure.md) |
| 7 | [Development Workflow](fase-6-delivery/07-development-workflow.md) |

---

## Status Dokumen

Semua dokumen di repo ini adalah **draft terstruktur (v0.1)** — kerangka + konten kontekstual sebagai titik awal. Bagian yang perlu diisi detail spesifik ditandai dengan `> TODO:` atau blok **Perlu Diputuskan**.

## Disclaimer

Sistem ini adalah alat **riset dan edukasi**. Output-nya bukan nasihat investasi, bukan ajakan membeli/menjual efek, dan bukan produk yang diatur sebagai penasihat investasi berlisensi. Regulasi OJK/BEI dijadikan **konteks analisis**, bukan sumber rekomendasi. Keputusan investasi tetap tanggung jawab pengguna.
