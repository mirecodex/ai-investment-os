# Deployment

**Fase:** 4 — Engineering · **Status:** Draft v0.1

## 1. Environment

- **dev** → **staging** → **prod**, konfigurasi via env + secret manager.
- Data provider "sandbox" bila tersedia untuk staging.

## 2. CI/CD

```
Commit → Lint & Test → Build image → Eval AI (regression prompt) → Deploy staging
       → Smoke test → Approval → Deploy prod → Monitor
```

- **AI regression gate**: perubahan prompt/model wajib lulus Evaluation Framework sebelum promote.

## 3. Strategi Rilis

- Rilis bertahap (canary) untuk perubahan berisiko.
- Feature flags: aktifkan fitur bertahap (sesuai visi "fondasi dulu, fitur menyusul").
- Rollback cepat (image sebelumnya + versi prompt sebelumnya).

## 4. Migrasi & Versi

- Migrasi DB terkontrol.
- Versi prompt & model dicatat pada tiap rekomendasi (reprodusibilitas).

## 5. Operasional

- Backup & restore teruji.
- Runbook insiden (provider down, biaya melonjak, data telat).

> TODO: Pilih tooling CI/CD & definisikan gate kualitas AI konkret.
