# Explainability Engine

**Fase:** 2 — AI Architecture · **Status:** Draft v0.1

## 1. Prinsip

Explainability adalah **fitur inti**, bukan tambahan. Setiap output harus bisa menjawab: *"Kenapa kesimpulan ini?"* dengan evidence yang dapat ditelusuri.

## 2. Komponen Penjelasan

1. **Ringkasan keputusan** — BUY/HOLD/SELL + confidence.
2. **Alasan utama** — 2–4 poin inti (dari committee).
3. **Evidence** — kutipan/referensi ke sumber (news id, laporan, flow).
4. **Argumen Bull vs Bear** — ringkas, agar seimbang.
5. **Rule yang terpicu** — jika keputusan dibatasi rule, tampilkan aturannya.
6. **Caveat & risiko** — apa yang bisa membuat thesis salah.

## 3. Audit Trail

Setiap run menyimpan jejak lengkap: analis mana dipanggil, evidence apa dipakai, rule apa terpicu, versi prompt & model. Berguna untuk debugging, kepercayaan, dan kepatuhan.

## 4. Contoh Output (Telegram)

```
BBCA — HOLD (Confidence 71%)

Alasan:
• Fundamental kuat (ROE tinggi, kualitas aset baik)
• Namun sentimen berita 7 hari terakhir negatif
• Foreign net sell signifikan minggu ini

Rule terpicu: R1 (fundamental kuat + sentimen negatif + foreign sell → HOLD)

Risiko thesis: pembalikan foreign flow / rilis laporan positif.
Bukti: [3 berita], [data flow], [rasio Q]

Bukan nasihat investasi.
```

## 5. Anti Black-Box

- Dilarang menyajikan kesimpulan tanpa evidence.
- Confidence rendah → penjelasan menekankan ketidakpastian.

> TODO: Standarkan template penjelasan untuk Telegram, alert, dan (nanti) dashboard.
