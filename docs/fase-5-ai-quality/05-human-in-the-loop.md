# Human-in-the-Loop (HITL)

**Fase:** 5 — AI Quality · **Status:** Draft v0.1

## 1. Tujuan

Menyisipkan pengawasan manusia pada titik berisiko tinggi — untuk kualitas, kepercayaan, dan kepatuhan.

## 2. Kapan Manusia Dilibatkan

| Trigger | Aksi HITL |
|---------|-----------|
| Confidence rendah (< ambang) | Tandai untuk review sebelum ditonjolkan |
| Keputusan kontradiktif vs rule | Review manual |
| Emiten sensitif / event besar | Review sebelum broadcast |
| Feedback pengguna negatif | Masuk antrean tinjauan |

## 3. Mekanisme

- **Review queue**: rekomendasi berisiko masuk antrean sebelum dikirim luas.
- **Feedback loop**: pengguna menilai kegunaan (👍/👎) → masuk episodic memory.
- **Override & anotasi**: reviewer bisa menandai kesalahan untuk perbaikan prompt/rule.

## 4. Peran

- **Domain reviewer** (paham pasar): validasi reasoning.
- **Ops**: pantau kualitas & insiden.

## 5. Umpan Balik ke Sistem

Hasil review → perbaikan prompt/rule/golden set (lihat Continuous Learning). HITL **bukan** bottleneck permanen; ambangnya diperketat seiring kepercayaan meningkat.

> TODO: Rancang UI/alur review & kebijakan kapan wajib HITL.
