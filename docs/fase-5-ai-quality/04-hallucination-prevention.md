# Hallucination Prevention

**Fase:** 5 — AI Quality · **Status:** Draft v0.1

## 1. Prinsip Inti

Agent **hanya** menalar dari evidence terkurasi. Dilarang mengarang angka/fakta. Tidak ada evidence → tidak ada klaim.

## 2. Lapisan Pertahanan

1. **Grounding**: seluruh fakta berasal dari knowledge base (RAG), bukan memori model.
2. **Evidence gating**: retrieval kosong/lemah → agent wajib menyatakan "bukti tidak cukup" → keputusan HOLD/abstain (Decision Engine R2).
3. **Structured output + validasi**: setiap klaim harus punya `EvidenceRef`; output tanpa evidence ditolak.
4. **Self-verification**: agent memeriksa tiap klaim sebelum menutup.
5. **Numeric guard**: angka (harga, rasio) hanya boleh dari data terstruktur, bukan digenerate LLM.
6. **Cross-check**: bandingkan klaim dengan data terstruktur bila memungkinkan.

## 3. Deteksi

- Validator otomatis: klaim tanpa evidence → flag/reject.
- Audit trail memudahkan penelusuran sumber tiap pernyataan.

## 4. Penanganan Ketidakpastian

- Bila data konflik/kurang → nyatakan eksplisit + turunkan confidence.
- Lebih baik "tidak cukup bukti" daripada mengarang.

> TODO: Implementasi validator evidence & aturan numeric-guard di layer output.
