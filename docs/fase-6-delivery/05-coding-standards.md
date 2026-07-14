# Coding Standards

**Fase:** 6 — Delivery · **Status:** Draft v0.1

## 1. Prinsip

Kode konsisten, teruji, mudah diaudit — penting untuk sistem AI ber-reasoning yang harus dapat ditelusuri.

## 2. Umum

- Konvensi penamaan & format otomatis (formatter + linter di CI).
- Type hints/typing kuat; validasi schema I/O (mis. pydantic-like).
- Fungsi kecil, single responsibility; core bebas dari detail interface.
- Dependency injection untuk provider (LLM/data) agar mudah di-mock.

## 3. Khusus AI

- **Prompt sebagai artefak berversi** (prompt registry), bukan string acak di kode.
- **Schema output** tiap agent didefinisikan & divalidasi.
- **Evidence wajib**: helper yang memaksa klaim membawa `EvidenceRef`.
- Tidak ada angka finansial di-hardcode dari LLM (numeric-guard).

## 4. Testing

- Unit test untuk rules/decision engine (deterministik).
- Contract test untuk pipeline & API.
- Eval test (regression AI) di CI untuk perubahan prompt/model.

## 5. Dokumentasi

- Docstring + ADR (Architecture Decision Records) untuk keputusan penting.
- Setiap modul menautkan ke dokumen fase terkait.

> TODO: Pilih bahasa & tooling final (linter, formatter, test runner) + template ADR.
