# Multi-Agent Architecture

**Fase:** 2 — AI Architecture · **Status:** Draft v0.1

## 1. Konsep: Investment Committee

Inti pembeda sistem. Bukan sekadar "Bull vs Bear", melainkan simulasi **rapat analis** berlapis: analis spesialis → sintesis Bull/Bear → komite → CIO → laporan.

```
                         Research Manager
                                │
      ┌────────┬────────┬───────┼────────┬────────┬────────┬────────┐
   Technical Fundamental Quant  News   Social  Macro  Foreign   Sector
   Analyst   Analyst   Analyst Analyst Analyst Analyst Flow      Rotation
      └────────┴────────┴───────┼────────┴────────┴────────┴────────┘
                                ↓
                          Bull Manager
                                ↓
                          Bear Manager
                                ↓
                      Investment Committee
                                ↓
                    Chief Investment Officer (CIO)
                                ↓
                       Telegram Report
```

## 2. Peran Lapisan

| Lapisan | Tugas |
|---------|-------|
| **Research Manager** | Orkestrasi: menentukan analis mana yang relevan, membagi tugas, mengumpulkan hasil. |
| **Specialist Analysts** | Menganalisis dari sudut masing-masing (lihat Agent Specifications). |
| **Bull / Bear Manager** | Menyusun argumen terkuat pro & kontra dari evidence yang ada. |
| **Investment Committee** | Menimbang Bull vs Bear, memeriksa konsistensi & rule. |
| **CIO** | Keputusan akhir + confidence + reasoning ringkas. |

## 3. Prinsip

- **Setiap agent hanya menerima data terkurasi** dari knowledge base (bukan internet mentah).
- **Setiap agent wajib mengembalikan evidence** untuk klaimnya.
- **Keputusan CIO tunduk pada Decision Engine** (rule engine + evidence gating).
- **Konteks market** (Market Brief) diinjeksikan ke semua agent.

## 4. Mode Eksekusi

- **On-demand:** dipicu perintah pengguna (`/analyze <ticker>`).
- **Scheduled:** Market Brief harian & pemantauan watchlist.
- **Event-driven:** dipicu berita/flow signifikan.

## 5. Trade-off

Multi-agent = kualitas & transparansi lebih tinggi, tapi biaya token & latency lebih besar. Mitigasi: routing (hanya panggil analis relevan), caching konteks, model tiering (lihat Cost Estimation).

> TODO: Definisikan protokol pesan antar-agent (skema input/output baku).
