# Fundamental Pipeline

**Fase:** 3 — Data Platform · **Status:** Draft v0.1

## 1. Tujuan

Menyediakan data fundamental terstruktur (laporan keuangan, rasio, valuasi, aksi korporasi) untuk Fundamental Analyst.

## 2. Alur

```
Laporan Emiten/BEI → Ingest → Parse → Normalize → Compute Ratios → Store → KB(fundamental)
```

## 3. Data Inti

| Kelompok | Contoh |
|----------|--------|
| Laba rugi | Pendapatan, laba bersih, margin |
| Neraca | Aset, liabilitas, ekuitas |
| Arus kas | Operasi, investasi, pendanaan |
| Rasio | ROE, ROA, PER, PBV, DER, NIM (bank) |
| Aksi korporasi | Dividen, right issue, split, buyback |
| Valuasi | Relatif (sektor) & tren historis |

## 4. Pemrosesan

- Parse laporan (kuartalan/tahunan) → normalisasi akun.
- Hitung rasio konsisten lintas emiten & waktu.
- Tandai event material (aksi korporasi) untuk event processing.

## 5. Konteks Sektoral

Rasio dibandingkan **dalam sektor** (bank ≠ komoditas ≠ consumer). Domain KB menyimpan benchmark sektor.

## 6. Kualitas

- Validasi konsistensi antar-periode.
- Sumber resmi diutamakan; catat tanggal rilis.

> TODO: Tetapkan sumber laporan, parser, dan daftar rasio standar per sektor.
