# API Design

**Fase:** 4 — Engineering · **Status:** Draft v0.1

## 1. Tujuan

API internal (dan nanti publik) agar core engine dapat dipakai lintas interface. Konsisten, ber-versi, dan aman.

## 2. Endpoint Inti (draft)

| Method | Path | Fungsi |
|--------|------|--------|
| GET | `/v1/market/brief` | Market Brief hari ini |
| POST | `/v1/analysis` | Jalankan analisis emiten `{ticker}` |
| GET | `/v1/analysis/{id}` | Ambil hasil analisis + explainability |
| GET | `/v1/tickers/{ticker}` | Profil emiten + data terkini |
| GET/POST/DELETE | `/v1/watchlist` | Kelola watchlist user |
| GET | `/v1/alerts` | Riwayat alert |

## 3. Konvensi

- **Versioning** di path (`/v1`).
- **Auth** via token (lihat Authentication).
- **Response** JSON konsisten: `data`, `meta`, `error`.
- **Explainability** disertakan pada hasil analisis (evidence, rules, confidence).
- **Idempotency-Key** untuk POST analisis event-driven.

## 4. Contoh Response Analisis

```json
{
  "data": {
    "ticker": "BBCA",
    "decision": "HOLD",
    "confidence": 0.71,
    "reasons": ["..."],
    "rules_triggered": ["R1"],
    "evidence": [{"source": "news", "ref": "..."}]
  },
  "meta": {"prompt_version": "...", "model": "..."},
  "error": null
}
```

## 5. Non-Fungsional

- Rate limiting, pagination, error taxonomy jelas.
- Disclaimer disertakan di payload rekomendasi.

> TODO: Spesifikasi OpenAPI lengkap + skema error.
