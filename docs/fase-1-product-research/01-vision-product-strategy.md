# Vision & Product Strategy

**Fase:** 1 — Product & Research · **Status:** Draft v0.1

## 1. Visi

Membangun **AI Investment OS** untuk pasar saham Indonesia — sebuah sistem yang memahami konteks IDX secara mendalam, melakukan riset ekuitas layaknya tim analis profesional, dan menyajikan rekomendasi yang transparan beserta alasannya. Telegram adalah antarmuka pertama; core engine dirancang modular agar bisa berkembang menjadi dashboard web, API internal, alert, dan simulasi portfolio tanpa mengubah fondasi.

## 2. Problem Statement

Investor ritel Indonesia (mayoritas pengguna Stockbit) menghadapi:
- Banjir informasi (berita, cuitan, laporan) tanpa waktu/kemampuan mengolahnya.
- Sulit menghubungkan peristiwa makro (BI Rate, Rupiah, harga komoditas) ke emiten spesifik.
- Rekomendasi yang beredar sering tanpa alasan yang bisa ditelusuri (black box, "pom-pom").
- Tools global tidak paham nuansa lokal (konglomerasi, foreign flow, sektor komoditas).

## 3. Solusi

Sebuah platform riset AI yang: memahami kondisi market harian (Market Brief), mengalirkan semua data lewat pipeline terkontrol, menjalankan analisis multi-agent (Investment Committee), lalu menghasilkan rekomendasi ber-*confidence* dan ber-*reasoning* yang dibatasi rule engine.

## 4. Positioning

> "Bloomberg Terminal versi AI, tapi paham Indonesia."

Bukan sinyal instan, bukan auto-trade. Yang dijual adalah **kualitas reasoning dan konteks lokal**.

## 5. Prinsip Strategi Produk

1. **Depth over breadth** — kuasai satu market (IDX) dengan sangat baik dulu.
2. **Explainability sebagai fitur inti**, bukan tambahan.
3. **Modular** — interface bisa berganti, core tetap.
4. **Trust by design** — evidence-based, rule-constrained, dengan disclaimer jelas.

## 6. Tujuan & Metrik Utara (North Star)

- **North Star Metric:** jumlah rekomendasi yang dibaca-tuntas dan dinilai "berguna" oleh pengguna per minggu.
- Metrik pendukung: retensi mingguan, akurasi arah rekomendasi (dievaluasi via backtesting), waktu dari peristiwa → insight.

## 7. Non-Goals (V1)

- Bukan eksekusi order otomatis.
- Bukan market selain IDX.
- Bukan penasihat investasi berlisensi.

> TODO: Tetapkan target kuantitatif (mis. jumlah emiten ter-cover di MVP, target pengguna beta).
