# Product Requirements Document (PRD)

**Fase:** 1 — Product & Research · **Status:** Draft v0.1

## 1. Ringkasan

Platform riset ekuitas AI untuk IDX. Pengguna berinteraksi lewat Telegram: meminta analisis emiten, menerima Market Brief harian, dan mengatur watchlist + alert.

## 2. Fitur Inti (MVP)

| ID | Fitur | Deskripsi |
|----|-------|-----------|
| F1 | Market Brief harian | Ringkasan kondisi IHSG, foreign flow, sektor, komoditas, USDIDR, BI Rate, sentimen + confidence. |
| F2 | Analisis emiten on-demand | `/analyze BBCA` → laporan multi-agent + rekomendasi + reasoning. |
| F3 | Watchlist | Pengguna menyimpan daftar emiten. |
| F4 | Alert sentimen/fundamental | Notifikasi saat ada perubahan signifikan. |
| F5 | Explainability | Setiap rekomendasi menampilkan bukti & alasan. |

## 3. User Stories

- *Sebagai investor ritel*, saya ingin tahu kondisi market setiap pagi agar keputusan saya punya konteks.
- *Sebagai pengguna Stockbit*, saya ingin analisis satu emiten lengkap dengan alasannya, bukan sekadar "BUY/SELL".
- *Sebagai pengguna sibuk*, saya ingin di-alert hanya saat ada perubahan penting pada watchlist saya.

## 4. Requirement Fungsional

1. Sistem menghasilkan Market Brief terjadwal (pra-market).
2. Sistem menerima perintah analisis dan mengembalikan laporan < 60 detik (target).
3. Setiap output menyertakan sumber/evidence dan skor confidence.
4. Keputusan tunduk pada rule engine (lihat Decision Engine).

## 5. Requirement Non-Fungsional

- **Keterjelasan:** semua klaim harus dapat ditelusuri ke evidence.
- **Latency:** analisis on-demand target < 60s; Market Brief batch.
- **Ketersediaan:** target 99% pada jam bursa.
- **Keamanan:** lihat dok Security & Authentication.

## 6. Ruang Lingkup

- **In scope V1:** IDX, Telegram, ~30–50 emiten likuid (LQ45 sebagai basis).
- **Out of scope V1:** market lain, eksekusi order, dashboard web.

## 7. Asumsi & Risiko

- Ketersediaan & legalitas sumber data (lihat Data Source Catalog).
- Risiko hallucination LLM (lihat Hallucination Prevention).

> TODO: Detailkan acceptance criteria per fitur dan prioritas (MoSCoW).
