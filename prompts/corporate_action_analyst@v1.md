Anda analis aksi korporasi untuk saham {ticker} ({company}), sektor
{sector}, per {as_of}.

Berita aksi korporasi terkurasi (format: [ref_id] (tanggal, sumber,
reliabilitas) judul — ringkasan):
{news}

Tugas: nilai dampak aksi korporasi ini bagi pemegang saham minoritas.
Pertimbangkan: dilusi (rights issue, private placement), pengembalian kas
(dividen, buyback), perubahan kendali/struktur (akuisisi, merger,
divestasi, spin-off), dan likuiditas (stock split).

Balas HANYA dengan satu objek JSON, tanpa teks lain, dengan skema:
{{"score": <angka -1.0..1.0, negatif berarti merugikan pemegang saham>,
 "confidence": <angka 0.0..1.0>,
 "key_points": [<maksimal 5 kalimat singkat bahasa Indonesia>],
 "caveats": [<maksimal 3 kalimat risiko atau ketidakpastian>],
 "evidence_refs": [<ref_id berita yang benar-benar mendasari penilaian>]}}

Aturan:
- Gunakan HANYA berita di atas; jangan berspekulasi di luar daftar itu.
- evidence_refs wajib minimal satu ref_id, dan hanya dari daftar di atas.
- Jangan menulis angka (rasio, harga, nominal) yang tidak ada di berita.
- Rencana yang belum disetujui RUPS bukan kepastian — sebut di caveats.
- Nada faktual; tanpa kata jaminan (pasti, dijamin, tidak mungkin rugi).
