# Infrastructure

**Fase:** 4 — Engineering · **Status:** Draft v0.1

## 1. Komponen

| Komponen | Peran |
|----------|-------|
| App/API service | Core engine + interface adapters |
| Worker | Job analisis multi-agent (async) |
| Scheduler | Batch (Market Brief, re-embedding) |
| Message broker | Event-driven pipeline |
| Databases | Relational, time-series, vector, cache |
| Object storage | Artefak & backup |
| LLM gateway | Abstraksi provider LLM + tiering |

## 2. Prinsip

- **Stateless services** + state di datastore → mudah diskalakan.
- **Env-based config** & secret manager (tak ada kredensial di kode).
- **IaC** (Infrastructure as Code) untuk reprodusibilitas.
- **Region**: pertimbangkan latency ke pengguna Indonesia & sumber data.

## 3. Skalabilitas

- Worker analisis di-scale horizontal (beban puncak jam bursa).
- Antrian meredam lonjakan event.
- Cache Market Brief & profil emiten.

## 4. Keandalan

- Health check, auto-restart, backup terjadwal.
- Pemisahan environment: dev / staging / prod.

> TODO: Pilih cloud/provider, container orchestration, & topologi jaringan.
