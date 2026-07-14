# Development Workflow

**Fase:** 6 — Delivery · **Status:** Draft v0.1

## 1. Alur Branch & Review

```
main (protected)
  └── feature/* → PR → review → CI (lint, test, eval AI) → merge → deploy staging
```

- PR kecil & fokus; wajib review.
- Perubahan prompt/rule/model **wajib** menyertakan hasil eval (regression).

## 2. Definition of Done

- Kode + test lulus; lint bersih.
- Perubahan AI lulus Evaluation Framework.
- Dokumentasi/ADR diperbarui bila keputusan berubah.
- Observability/log memadai untuk fitur baru.

## 3. Environments

- dev (lokal) → staging (data sandbox) → prod.
- Feature flags untuk aktivasi bertahap.

## 4. Rilis

- Canary untuk perubahan berisiko; rollback cepat (image + versi prompt).
- Catat versi prompt/model pada rekomendasi (reprodusibilitas).

## 5. Ritme Tim

- Perencanaan per tahap roadmap; retro untuk kualitas.
- Triage feedback pengguna & hasil HITL → backlog perbaikan.

## 6. Kualitas sebagai Budaya

- Grounding & explainability bukan opsional.
- "Tidak cukup bukti" adalah output yang sah dan dihargai.

> TODO: Tetapkan cadence rilis, aturan branch, & template PR.
