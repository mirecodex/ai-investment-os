# Telegram Bot UX

**Fase:** 4 — Engineering · **Status:** Draft v0.1

## 1. Peran

Antarmuka pertama. Harus ringkas, jelas, mobile-friendly, dan selalu menyertakan alasan + disclaimer.

## 2. Perintah Inti

| Perintah | Fungsi |
|----------|--------|
| `/start` | Onboarding + disclaimer |
| `/brief` | Market Brief hari ini |
| `/analyze <TICKER>` | Analisis emiten (mis. `/analyze BBCA`) |
| `/watchlist` | Lihat/kelola watchlist |
| `/add <TICKER>` / `/remove <TICKER>` | Tambah/hapus watchlist |
| `/alerts` | Atur & lihat alert |
| `/help` | Bantuan |

## 3. Pola Interaksi

- **Progressive disclosure**: tampilkan ringkasan dulu → tombol "Lihat detail/evidence".
- **Inline buttons** untuk aksi (tambah watchlist, minta detail Bull/Bear).
- **Loading state**: beri tahu "sedang menganalisis..." (analisis bisa >10s).
- **Pesan pendek** + format rapi (bold hemat, poin ringkas).

## 4. Format Output

Ikuti template Explainability Engine: keputusan + confidence → alasan → rule → risiko → evidence → disclaimer.

## 5. Prinsip UX

- Jangan menjanjikan profit; nada hati-hati saat confidence rendah.
- Hormati zona waktu WIB untuk brief harian.
- Hindari spam notifikasi (alert hanya untuk perubahan material).

> TODO: Rancang copy onboarding, contoh percakapan, & desain inline keyboard.
