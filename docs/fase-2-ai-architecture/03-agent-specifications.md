# Agent Specifications

**Fase:** 2 — AI Architecture · **Status:** Draft v0.1

Spesifikasi tiap agent: tujuan, input, output, sumber evidence, dan aturan.

## Format Output Baku (semua analis)

```
AnalystOpinion:
  role: str
  stance: enum(POSITIVE, NEUTRAL, NEGATIVE)
  key_points: list[str]
  evidence: list[EvidenceRef]     # wajib, menunjuk ke knowledge base
  confidence: float               # 0..1
  caveats: list[str]
```

## Daftar Agent

### Research Manager
Orkestrator. Memilih analis relevan berdasarkan ticker & konteks; menggabungkan hasil.

### Technical Analyst
Input: harga/volume, indikator. Output: tren, level kunci, momentum. Evidence: market data.

### Fundamental Analyst
Input: laporan keuangan, rasio, valuasi. Output: kualitas & valuasi emiten. Evidence: fundamental pipeline.

### Quant Analyst
Input: faktor kuantitatif (volatilitas, beta, faktor). Output: skor kuantitatif. Evidence: market data.

### News Analyst
Input: berita terkurasi + importance score + sentiment. Output: dampak berita. Evidence: news pipeline.

### Social Analyst
Input: mention sosial (bebas spam/bot) + sentiment. Output: sentimen ritel. Evidence: social pipeline.

### Macro Analyst
Input: BI Rate, USDIDR, komoditas (batu bara, nikel, CPO, emas), kebijakan. Output: konteks makro → dampak emiten/sektor.

### Foreign Flow Analyst
Input: net foreign buy/sell. Output: tekanan/dukungan flow, terutama big-cap.

### Sector Rotation Analyst
Input: performa antar-sektor. Output: sektor kuat/lemah & posisi emiten dalam rotasi.

### Bull Manager / Bear Manager
Menyusun argumen terkuat pro/kontra dari `analyst_outputs` + evidence.

### Investment Committee
Menimbang Bull vs Bear, cek konsistensi & rule, catat perbedaan pendapat.

### Chief Investment Officer (CIO)
Keputusan akhir (BUY/HOLD/SELL) + confidence + reasoning ringkas, tunduk Decision Engine.

> TODO: Tuliskan prompt & schema I/O detail per agent (lihat Prompt Engineering Guide).
