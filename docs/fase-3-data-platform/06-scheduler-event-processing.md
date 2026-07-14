# Scheduler & Event Processing

**Fase:** 3 — Data Platform · **Status:** Draft v0.1

## 1. Tujuan

Mengatur pekerjaan terjadwal (batch) dan reaksi terhadap event (realtime) yang menggerakkan pipeline & analisis.

## 2. Jadwal Utama (WIB)

| Waktu | Job |
|-------|-----|
| Pra-market | Susun Market Brief harian |
| Intraday | Update market data, foreign flow, mention sosial |
| Pasca-market | Rekap harian, update fundamental bila ada rilis |
| Berkala | Re-embedding KB, evaluasi, backup |

## 3. Event-Driven

- **Trigger:** berita material (importance tinggi), lonjakan sentimen, foreign flow ekstrem, aksi korporasi.
- **Aksi:** perbarui KB → cek watchlist terdampak → jalankan analisis ringkas → kirim alert bila melewati ambang.

## 4. Arsitektur

- **Scheduler** (cron/queue) untuk batch.
- **Event bus/queue** untuk realtime & dekopling pipeline.
- **Idempotency** & dedup agar event ganda tak menghasilkan alert ganda.
- **Retry + dead-letter** untuk kegagalan.

## 5. Kalender Bursa

Hormati hari libur bursa & jam sesi; jangan buat Market Brief saat bursa tutup (kecuali ringkasan mingguan).

> TODO: Pilih scheduler & message broker; definisikan daftar event & ambang alert.
