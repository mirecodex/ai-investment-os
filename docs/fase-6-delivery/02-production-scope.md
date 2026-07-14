# Production Scope

**Fase:** 6 — Delivery · **Status:** Draft v0.1

## 1. Dari MVP ke Produksi

Memperluas cakupan, keandalan, dan kualitas hingga layak dipakai luas — tetap IDX-first.

## 2. Tambahan di Produksi

- **Cakupan emiten** diperluas (di luar LQ45, dengan penanganan likuiditas rendah).
- **Analis lengkap** (semua peran Investment Committee aktif).
- **Alert event-driven** matang (sentimen/fundamental/flow).
- **Dashboard web** (interface kedua) memakai core yang sama.
- **API internal** untuk integrasi.
- **Simulasi portfolio** & evaluasi strategi.
- **HITL & continuous learning** berjalan rutin.

## 3. Kualitas & Operasional

- SLO ketersediaan jam bursa; observability & alerting matang.
- Evaluation gate di CI/CD; backtesting rutin.
- Keamanan & kepatuhan diperkuat (audit, retensi, disclaimer).

## 4. Skalabilitas

- Worker analisis auto-scale; caching & tiering model untuk biaya.
- Multi-interface stabil di atas core modular.

## 5. Kesiapan Multi-Market (masa depan)

- Arsitektur adapter siap; menambah US market = adapter + pipeline baru, bukan rewrite.

> TODO: Tetapkan kriteria "production-ready" (SLO, coverage, kualitas) yang terukur.
