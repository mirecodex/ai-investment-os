# Cost Estimation

**Fase:** 4 — Engineering · **Status:** Draft v0.1

## 1. Sumber Biaya

| Komponen | Pemicu biaya |
|----------|--------------|
| LLM tokens | Multi-agent = banyak panggilan; terbesar biasanya di sini |
| Embedding | Indexing & re-embedding KB |
| Data providers | Lisensi market/news/fundamental |
| Infrastruktur | Compute worker, DB, vector DB, storage |
| Message broker/cache | Event & caching |

## 2. Strategi Efisiensi

1. **Model tiering**: model kecil untuk tugas ringan (ekstraksi, klasifikasi), model besar untuk reasoning committee/CIO.
2. **Routing analis**: hanya panggil analis relevan per ticker/konteks.
3. **Caching**: Market Brief, profil emiten, hasil retrieval.
4. **Batching**: proses berita/embedding secara batch.
5. **Truncation cerdas**: kirim ringkasan evidence, bukan teks penuh.

## 3. Kerangka Estimasi (isi angka nyata)

```
biaya_analisis ≈ Σ(analis_dipanggil × token_rata2 × harga_token)
              + biaya_retrieval + overhead
biaya_harian  ≈ biaya_market_brief + (jumlah_analisis × biaya_analisis)
              + biaya_pipeline (news/social/fundamental)
```

## 4. Kontrol Anggaran

- Budget alert per hari (lihat Observability).
- Batas rate per user untuk cegah penyalahgunaan.

> TODO: Isi harga token provider terpilih & proyeksi volume untuk hitung biaya/bulan.
