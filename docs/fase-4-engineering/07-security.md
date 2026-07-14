# Security

**Fase:** 4 — Engineering · **Status:** Draft v0.1

## 1. Prinsip

Keamanan & privasi sejak desain. Minimalkan data pribadi; lindungi kredensial; batasi akses.

## 2. Area Utama

| Area | Kontrol |
|------|---------|
| Secrets | Secret manager, rotasi, tak ada kredensial di repo |
| Transport | TLS di semua endpoint |
| Auth | Token + scope + rate limit (lihat Authentication) |
| Data | Enkripsi at-rest, minimisasi PII, retensi terbatas |
| Input | Validasi & sanitasi perintah pengguna |
| LLM | Guard prompt injection, batasi tool/aksi agent |
| Dependency | Scan kerentanan, pinning versi |

## 3. Prompt Injection & Data Beracun

- Data eksternal (berita/sosial) diperlakukan sebagai **konten**, bukan instruksi.
- Pipeline membersihkan & menandai sumber; agent tak mengeksekusi instruksi yang tertanam dalam data.

## 4. Privasi Pengguna

- Simpan minimal (telegram_id, watchlist, preferensi).
- Hak hapus data pengguna.
- Kepatuhan terhadap regulasi perlindungan data yang berlaku.

## 5. Kepatuhan Domain

- Produk bukan nasihat investasi berlisensi; sertakan disclaimer.
- Hormati ToS & hak cipta sumber data.

> TODO: Susun threat model + checklist hardening sebelum produksi.
