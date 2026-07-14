# Social Intelligence Pipeline

**Fase:** 3 — Data Platform · **Status:** Draft v0.1

## 1. Tujuan

Mengukur sentimen ritel Indonesia dari media sosial secara **bersih** — bebas spam & bot — untuk Social Analyst.

## 2. Alur

```
Twitter/X, Forum → Crawler → Mention → Ticker Detection → Spam Detection
                → Bot Detection → Sentiment → Knowledge Base
```

## 3. Tahapan

| Tahap | Fungsi |
|-------|--------|
| Crawler | Ambil mention terkait emiten/kata kunci (hormati ToS platform). |
| Mention | Isolasi unit percakapan relevan. |
| Ticker Detection | Petakan cashtag/nama → ticker IDX. |
| Spam Detection | Buang promosi/pom-pom/duplikat. |
| Bot Detection | Saring akun otomatis/koordinasi. |
| Sentiment | Sentimen ritel per emiten. |
| KB | Simpan agregat sentimen + metadata. |

## 4. Kehati-hatian

- **Rentan manipulasi** (pom-pom, buzzer) → sinyal sosial hanya salah satu input, bukan penentu.
- Bobot sosial lebih rendah dibanding fundamental/flow dalam Decision Engine.
- Privasi: simpan agregat, minimalkan data pribadi.

## 5. Output

- Skor sentimen ritel per emiten + volume mention + tren.

> TODO: Tetapkan sumber sosial legal, model spam/bot, dan skema agregasi.
