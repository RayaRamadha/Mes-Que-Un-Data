# Ball possession dari tracking otomatis — dokumen teknis

**Tim:** Més Que Un Data · **Repo:** _(URL publik)_ · **File:** _(nama final ditetapkan di Fase 5)_ · **SHA-256 CSV:** _(diisi saat submit)_

> Kerangka sesuai SUBMISSION.md. Diisi bertahap selama Fase 1–3, difinalkan di Fase 4.3; ekspor ke PDF bernama tim.
> Hanya angka agregat — tidak ada data per frame di dokumen ini.

## 1. Ringkasan

_(3–5 kalimat: apa yang dibangun, ide utamanya, hasil pada GT publik dengan interval, dan cara reproduksi.)_

## 2. Pendekatan & alasannya

- Mengapa spellF1 membentuk desain (possession utuh, hukuman pergantian palsu dan D palsu).
- Arsitektur: bola mati (hidup/mati) → siapa yang menguasai (H/A) → decoder gabungan → penyempurnaan batas.
- Alternatif yang dipertimbangkan dan alasan tidak dipilih.

## 3. Aset yang dipakai & yang dibuang

| Aset | Dipakai? | Untuk apa / mengapa tidak |
|---|---|---|
| ATD tactical | | |
| Smart Tagging | | |
| Homography tactical | | |
| ATD + homography broadcast | | |
| Video tactical / broadcast | | |
| GT publik 5 menit | | hanya cek kebenaran pipeline |

## 4. Penanganan tracking yang hilang & berisik

- Bola hilang (41% frame dinilai, dalam blok panjang): …
- Slot track tanpa identitas, duplikat, celah pemain: …
- Lompatan posisi bola: …

## 5. Aturan possession yang diterapkan

- Bola mati (`D`): …
- Pergantian possession "terkontrol": …
- Bola lepas, duel, defleksi: …
- Restart (tim pengambil, termasuk throw-in yang tag-nya N/A): …
- Penggunaan `X`: …

## 6. Validasi

- Protokol (GT publik hanya cek kebenaran; proxy seluruh match; stabilitas parameter).
- Tabel ablation.
- Sensitivitas parameter utama.

## 7. Keterbatasan & yang akan diperbaiki dengan waktu lebih

…

## 8. Reproduksi

```bash
git clone --recurse-submodules <repo>
py -3.11 -m venv .venv && .venv\Scripts\python -m pip install -r requirements-lock.txt
powershell -ExecutionPolicy Bypass -File run_all.ps1      # → submissions/MesQueUnData_<versi>.csv
```

Waktu jalan total: … · Hash CSV yang dihasilkan harus sama dengan yang di atas.
