# News Intelligence Pipeline

**Fase:** 3 — Data Platform · **Status:** Draft v0.1

## 1. Tujuan

Mengubah berita mentah menjadi evidence terstruktur: ringkasan, entitas, ticker terpetakan, importance, dan sentimen. **Agent tidak pernah membaca berita mentah.**

## 2. Alur

```
News → Crawler → Cleaner → Summarizer → Entity Extraction → Ticker Mapping
     → Importance Score → Sentiment → Knowledge Base
```

## 3. Tahapan

| Tahap | Fungsi |
|-------|--------|
| Crawler | Ambil artikel dari sumber terdaftar (hormati ToS). |
| Cleaner | Buang boilerplate, iklan, duplikat. |
| Summarizer | Ringkas ke poin inti (hemat token, hindari reproduksi penuh). |
| Entity Extraction | Kenali emiten, tokoh, sektor, komoditas, kebijakan. |
| Ticker Mapping | Petakan entitas → ticker IDX (mis. "bank BCA" → BBCA). |
| Importance Score | Nilai seberapa material berita bagi emiten/sektor. |
| Sentiment | Sentimen (positif/negatif/netral) kontekstual pasar. |
| KB | Simpan sebagai evidence ber-metadata + timestamp. |

## 4. Pemetaan Konteks Lokal

Manfaatkan domain KB: "HET naik" → sektor terdampak; "harga CPO naik" → emiten sawit. Pemetaan ini yang membuat News Analyst relevan.

## 5. Kualitas

- Deteksi & buang hoaks/sumber tidak kredibel.
- Deduplikasi lintas media.
- Simpan hanya olahan, hormati hak cipta.

> TODO: Tetapkan model NER/summarizer & daftar sumber berita + skema evidence.
