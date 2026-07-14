# Authentication

**Fase:** 4 — Engineering · **Status:** Draft v0.1

## 1. Tujuan

Mengidentifikasi pengguna (awalnya via Telegram), mengamankan API, dan menyiapkan multi-interface.

## 2. Model

- **Telegram identity**: `telegram_id` sebagai identitas awal, dipetakan ke `user_id` internal.
- **API tokens**: token bearer untuk akses core API (internal/service-to-service).
- **Scopes/roles**: user biasa, admin, service.

## 3. Alur (Telegram)

1. `/start` → verifikasi `telegram_id` → buat/temukan `user_id`.
2. Simpan preferensi minimal; tak menyimpan PII berlebih.
3. Sesi ringan (percakapan) + long-term user memory (watchlist/preferensi).

## 4. Keamanan Token

- Token disimpan aman (secret manager), rotasi berkala.
- Verifikasi webhook Telegram (secret token) agar hanya request sah diterima.
- Rate limit per user & per token.

## 5. Multi-Interface (masa depan)

- Web/API: OAuth/OIDC atau token; pemetaan ke `user_id` yang sama → pengalaman konsisten lintas kanal.

> TODO: Pilih mekanisme token (JWT?), secret manager, & kebijakan rotasi.
