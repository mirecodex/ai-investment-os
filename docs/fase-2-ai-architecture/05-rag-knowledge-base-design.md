# RAG & Knowledge Base Design

**Fase:** 2 — AI Architecture · **Status:** Draft v0.1

## 1. Peran

Knowledge base (KB) adalah **satu-satunya** sumber fakta bagi agent. Semua pipeline data bermuara ke sini. Agent mengambil evidence via RAG (retrieval-augmented generation).

## 2. Isi Knowledge Base

| Koleksi | Isi | Sumber |
|---------|-----|--------|
| `news` | Berita terkurasi + ringkasan + entitas + sentimen + importance | News pipeline |
| `social` | Mention bersih (non-spam/bot) + sentimen | Social pipeline |
| `fundamental` | Laporan keuangan, rasio, aksi korporasi | Fundamental pipeline |
| `market` | Harga, volume, foreign flow, indeks | Market pipeline |
| `macro` | BI Rate, USDIDR, harga komoditas, kebijakan | Market/macro pipeline |
| `domain` | Peta emiten↔sektor↔driver, aturan bisnis, glosarium | Kurasi manual |

## 3. Strategi Retrieval

- **Hybrid search**: vektor (semantic) + keyword/metadata filter (ticker, tanggal, sumber, sektor).
- **Time-aware**: prioritaskan evidence terbaru; simpan timestamp.
- **Scoped retrieval**: analis hanya menarik koleksi yang relevan (Fundamental Analyst → `fundamental`).
- **Citation-ready**: tiap chunk membawa `EvidenceRef` (id, sumber, tanggal).

## 4. Chunking & Embedding

- Chunk berbasis dokumen semantik (paragraf/berita/laporan) dengan metadata kaya.
- Embedding multilingual yang kuat untuk Bahasa Indonesia.
- Re-embedding terjadwal saat model/embed berubah (versi index).

## 5. Kualitas & Anti-Halusinasi

- Evidence gating: jika retrieval kosong/lemah → agent tidak boleh mengklaim.
- Deduplikasi & filtering sumber tidak kredibel.

> TODO: Pilih vector DB, model embedding, dan skema metadata final (lihat Database & Vector Schema).
