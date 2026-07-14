# Database & Vector Schema

**Fase:** 3 — Data Platform · **Status:** Draft v0.1

## 1. Penyimpanan (gambaran)

| Store | Untuk |
|-------|-------|
| Relational (mis. Postgres) | Emiten, user, watchlist, rekomendasi, audit, rules |
| Time-series | Harga, volume, flow, indikator |
| Vector DB | Embedding evidence (news, social, fundamental, domain) |
| Cache (mis. Redis) | Market Brief, sesi, working memory |
| Object storage | Artefak mentah/olahan, backup |

## 2. Skema Relasional (ringkas)

```
tickers(ticker PK, nama, sektor, papan, ...)
users(user_id PK, telegram_id, preferensi, ...)
watchlist(user_id FK, ticker FK, created_at)
recommendations(id PK, ticker, decision, confidence, created_at,
                prompt_version, model_version)
evidence_refs(rec_id FK, source, ref_id, url_or_id, snippet_hash)
rule_triggers(rec_id FK, rule_id, effect)
outcomes(rec_id FK, horizon, actual_return, evaluated_at)
```

## 3. Skema Vektor (metadata per chunk)

```
{
  id, collection(news|social|fundamental|domain|macro),
  ticker[], sektor[], source, published_at, importance,
  sentiment, embedding[], text_summary
}
```

## 4. Prinsip

- **Citation-ready**: setiap chunk menyimpan referensi asal → mendukung explainability.
- **Time-aware**: `published_at` untuk retrieval terbaru.
- **Versioning**: catat versi embedding/model.
- **Retensi & PII**: minimalkan data pribadi (lihat Security).

> TODO: Finalisasi pilihan DB, index, dan DDL lengkap.
