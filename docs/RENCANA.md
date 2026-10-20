# Rencana Kerja — More than a Hack 2027, Phase 1 (Ball Possession)

> Dokumen hidup. Perbarui status di tabel **Progres** setiap selesai satu langkah, dan catat setiap
> eksperimen di `docs/experiment_log.md`. Semua angka di sini berasal dari dokumentasi resmi atau
> laporan agregat pipeline kita sendiri — bukan dari ground truth privat.

| | |
|---|---|
| Hari ini | Selasa, 20 Oktober 2026 (data dirilis) |
| Deadline | **Selasa, 17 November 2026** — target kirim **Senin, 16 November** (H-1 sebagai cadangan) |
| Metrik peringkat | `spellF1` (rata-rata F1 pencocokan possession pada IoU 0,3–0,7); tie-break `macroF1` |
| Batas bawah | spellF1 **0,2433** (`baseline_smooth50`, full match) |
| Syarat tim | **3–5 orang** — pastikan terpenuhi sebelum mendaftarkan submission |

---

## 1. Prinsip yang memandu semua keputusan

1. **Optimalkan possession utuh, bukan frame.** spellF1 menghitung tiap possession satu kali. Dua
   kesalahan paling mahal:
   - **pergantian palsu** (H H A H H) — satu possession benar pecah jadi tiga, tidak ada yang cocok;
   - **D palsu di tengah possession** (H D H) — juga memecah satu possession jadi dua.
   Maka setiap komponen harus lebih "pelit" mengganti keadaan daripada mengejar akurasi per frame.
2. **Ketepatan waktu transisi penting.** Telat 1 frame gratis, telat 8 frame → 0,89, telat 1 detik
   → 0,65. Setelah keputusan "ada pergantian", geser batasnya ke sentuhan pertama yang sebenarnya.
3. **GT publik (5 menit, 17 possession) hanya untuk cek kebenaran pipeline, bukan untuk memilih
   versi/parameter.** Satu possession = ±6 poin spellF1 di sana. Parameter dipilih dari prinsip
   fisik/sepak bola + *proxy metric* seluruh match (lihat §5), lalu dicek dengan bootstrap.
4. **Bola hilang 41% frame dinilai, dalam blok panjang** (median celah 268 frame ≈ 11 s). Model
   possession harus tetap bekerja tanpa bola — dari bentuk dan gerak tim.
5. **Reproduksibel sejak hari pertama.** Repo harus menghasilkan file yang *persis sama*. Tidak ada
   artefak di `cache/` yang kodenya tidak ada di repo (masalah `dead_scores.npz` v1 harus hilang).
6. **Data tidak keluar dari komputer.** Tidak di-commit, tidak dikirim ke LLM cloud. Notebook hanya
   mencetak angka agregat; output notebook dibersihkan sebelum commit bila memuat data per frame.

---

## 2. Struktur proyek (target)

Semua kode dalam **Jupyter notebook** dengan markdown yang menjelaskan setiap langkah.

```
C:\lomba barca\                       ← root repo git (nanti dipublikasikan)
├─ README.md                          cara install & reproduksi (1 perintah)
├─ requirements.txt                   versi dipin (numpy, pandas, jupyter, nbconvert, ...)
├─ .gitignore                         tactical/ broadcast/ cache/ submissions/ *.zip
├─ run_all.ps1 / run_all.sh           eksekusi notebook berurutan via nbconvert
├─ notebooks/
│  ├─ common.ipynb                    fungsi bersama (runs, viterbi, io) — dipanggil via %run
│  ├─ 00_setup_cek_data.ipynb         lingkungan, path, keselarasan frame, inventaris data
│  ├─ 01_preprocess.ipynb             ATD → array per frame video (meter, kecepatan, tim per slot) → cache/prep.npz, tags.csv
│  ├─ 02_eda_gt_publik.ipynb          memahami definisi D dan H/A pada GT publik
│  ├─ 03_bola_mati.ipynb              detektor bola mati → dead_mask, restarts
│  ├─ 04_fitur_possession.ipynb       fitur kontrol bola + bentuk tim per frame
│  ├─ 05_model_possession.ipynb       pseudo-label + model probabilitas H/A
│  ├─ 06_decoder_submission.ipynb     decoder H/A/D → submissions/<tim>.csv + validasi
│  ├─ 07_validasi_ablation.ipynb      proxy metric, bootstrap, tabel ablation
│  └─ 08_broadcast_opsional.ipynb     (stretch) selaraskan broadcast ke tactical
├─ docs/
│  ├─ RENCANA.md                      dokumen ini
│  ├─ experiment_log.md               satu baris per eksperimen
│  └─ technical_report.md             dokumen teknis untuk submission (→ <tim>.pdf)
├─ external/more-than-a-hack-2027/   repo resmi (git submodule): scorer, GT publik, games.py
├─ tactical/  broadcast/              data (gitignored, tidak pernah di-commit)
├─ cache/                             artefak antara (gitignored)
└─ submissions/                       file CSV (gitignored)
```

### Standar setiap notebook

1. **Judul & ringkasan** (markdown): tujuan, input, output, waktu jalan kira-kira.
2. **Sel parameter** (diberi tag `parameters`) — semua angka yang bisa diubah ada di satu tempat,
   masing-masing dengan alasan singkat.
3. Bagian-bagian bernomor; **setiap sel kode didahului markdown** yang menjelaskan *apa* dan *kenapa*.
4. Hanya mencetak/menampilkan **agregat** (jumlah, persentase, distribusi). Plot per-frame boleh
   untuk eksplorasi lokal, tapi output-nya dibersihkan sebelum commit.
5. **Sel cek akhir**: `assert` bahwa output ada, ukurannya benar, tidak ada NaN tak terduga.
6. **Ringkasan & keputusan** (markdown) di akhir: apa yang dipelajari, apa yang dipakai tahap berikut.
7. Deterministik: seed tetap, urutan tetap, tanpa paralelisme yang tidak deterministik.

Reproduksi seluruh pipeline (target):

```bash
jupyter nbconvert --to notebook --execute --inplace notebooks/00_setup_cek_data.ipynb   # ... dst. berurutan, lewat run_all
```

---

## 3. Fase dan langkah

### Fase 0 — Fondasi (20–22 Okt)

| # | Langkah | Selesai bila |
|---|---|---|
| 0.1 | Konfirmasi tim 3–5 orang & nama tim (nama file CSV/PDF = nama tim) | nama tim tertulis di README |
| 0.2 | Cek versi Python, buat venv, `requirements.txt` dipin | `pip install -r requirements.txt` bersih di venv baru |
| 0.3 | `git init`, `.gitignore`, repo resmi sebagai submodule, nbstripout | `git status` tidak menampilkan file data |
| 0.4 | Set `MTAH_DATA_DIR = C:\lomba barca`; samakan nama video broadcast (`-001`) | `games.require(...)` lolos untuk semua aset yang ada |
| 0.5 | Video tactical: ada (`BAR-ATH_tactical-002.mp4`); tidak dipakai sampai stretch 3.6 | keputusan tercatat di notebook 00 |
| 0.6 | `common.ipynb` + `00_setup_cek_data.ipynb` | notebook jalan via nbconvert tanpa error |
| 0.7 | Buat `docs/experiment_log.md` & kerangka `technical_report.md` | file ada |

### Fase 1 — Bangun ulang tahap 2–3 + submission pertama yang valid (22–26 Okt)

> Skrip `.py` lama sudah dihapus (hanya uji coba). Logika dan pelajarannya (lihat laporan lama di `cache/*.txt`)
> dibangun ulang sebagai notebook. Artefak lama di `cache/` (`prep.npz`, `dead_scores.npz`, `dead_v2.npz`, …) akan
> ditimpa/dihapus — tidak boleh ada notebook yang bergantung pada artefak tanpa kode.

| # | Langkah | Selesai bila |
|---|---|---|
| 1.1 | `01_preprocess.ipynb`: parsing ATD, meter, kecepatan bola, celah bola, tim per slot, arah serang, tag → frame | angka agregat sama dengan laporan lama `cache/report.txt` |
| 1.2 | `02_eda_gt_publik.ipynb`: diagnostik D (garis waktu, AUC fitur) + **analisis H/A**: kapan GT berganti tim, berapa lama bola tak terlihat di sekitar pergantian, jarak pemain terdekat saat ganti | ringkasan definisi "kontrol" versi GT tertulis di markdown |
| 1.3 | `03_bola_mati.ipynb`: fitur kolektif + Viterbi 2 keadaan (ide v2), aturan pasti (prior babak 2, gol→kick-off) ditulis di notebook | jalan dari `prep.npz` saja |
| 1.4 | Submission end-to-end paling sederhana: D dari tahap 3 + H/A dari baseline nearest-player yang dihaluskan di dalam segmen hidup | lolos `validate_submission.py`; tercatat di log |

**Gerbang Fase 1:** ada satu file valid yang bisa dihasilkan ulang dari nol dengan satu perintah. ✅ (20 Okt)

> **Penyesuaian setelah Fase 1:** v0 menunjukkan `D` palsu adalah hambatan terbesar (memakan frame hidup dan
> memecah possession). Langkah **3.1 (bola mati v3 → presisi)** dimajukan dan dikerjakan berdampingan dengan Fase 2.

### Fase 2 — Model possession v1 (27 Okt – 2 Nov)

Ide inti: **pisahkan "apakah bola hidup" (tahap 3) dari "siapa yang menguasai" (tahap 4), lalu
gabungkan dalam satu decoder yang menghukum pergantian keadaan.**

| # | Langkah | Detail |
|---|---|---|
| 2.1 | **Fitur kontrol bola** (bila bola terlihat) | jarak pemain terdekat tiap tim, selisihnya, berapa lama tim itu terdekat, kecepatan bola relatif pemain, perubahan arah/kecepatan bola (sentuhan) |
| 2.2 | **Fitur bentuk tim** (selalu tersedia, kunci saat bola hilang) | sentroid tim relatif arah serang, lebar/kedalaman/luas convex hull, garis pertahanan, kecepatan rata-rata ke arah gawang lawan, kekompakan; tim yang menyerang cenderung melebar dan maju, yang bertahan kompak di antara bola dan gawangnya |
| 2.3 | **Fitur Smart Tagging** | fase Build Up / Progression / Creating Chances / Attacking Transition → tim itu menguasai; Defending in … → tim itu *tidak* menguasai; tim restart set piece |
| 2.4 | **Pseudo-label tanpa GT** | frame di mana bola terlihat dan satu pemain jelas mengontrol (sangat dekat, lawan jauh, bertahan beberapa frame) → label H/A otomatis di seluruh match (puluhan ribu frame). Latih model bentuk-tim di sini, terapkan ke frame tanpa bola. GT publik **tidak** dipakai untuk melatih |
| 2.5 | **Model probabilitas** | regresi logistik sederhana dulu (numpy, mudah dijelaskan); naik ke gradient boosting hanya bila ablation membuktikan manfaatnya |
| 2.6 | **Decoder 3 keadaan (H/A/D)** | Viterbi/HSMM per babak: emisi dari P(D) tahap 3 dan P(H\|hidup) tahap 4; biaya pergantian H↔A dan hidup↔mati; durasi minimum possession; setelah D, tim pertama = tim restart |
| 2.7 | **Penyempurnaan batas** | geser setiap transisi ke sentuhan pertama yang paling masuk akal dalam jendela ±1 s |

**Gerbang Fase 2:** jumlah & durasi possession masuk akal (sekitar belasan detik rata-rata seperti
GT publik), dan lebih baik dari baseline di proxy metric seluruh match.

### Fase 3 — Peningkatan & pembuktian (3–9 Nov)

| # | Langkah | Detail |
|---|---|---|
| 3.1 | **Bola mati v3** | deteksi kejadian, bukan hanya fitur halus: bola keluar garis, bola diam di titik restart (busur sudut, garis samping, kotak 5,5 m, titik tengah), formasi khas (tembok, pemain menumpuk di kotak saat corner), awal/akhir jendela tag set piece (jendela tag panjangnya tetap 35 s / 5 s, jadi hanya titiknya yang bermakna). Target utama: **naikkan presisi D** (saat ini 0,47 dalam-sampel) tanpa menjatuhkan recall |
| 3.2 | **Tim pengambil throw-in & kick-off** (tag-nya N/A) | dari posisi pemain di dekat bola saat restart / tim lawan dari penyentuh terakhir |
| 3.3 | **Ablation** di `07_validasi_ablation.ipynb` | matikan satu komponen tiap kali (tag, bentuk tim, penyempurnaan batas, dst.), catat proxy metric + spellF1 publik + interval bootstrap |
| 3.4 | **Analisis sensitivitas** | biaya pergantian & durasi minimum: pilih nilai di *dataran stabil*, bukan di puncak tajam |
| 3.5 | (stretch) **Broadcast** di `08_broadcast_opsional.ipynb` | selaraskan waktu broadcast→tactical dengan mencocokkan posisi pemain (keduanya di koordinat lapangan 0–1). Manfaat: bola terlihat di sudut kamera lain, dan cuplikan replay/close-up (homography invalid) hampir selalu terjadi saat bola mati |
| 3.6 | (stretch) **Deteksi bola dari video tactical** untuk mengisi celah | hanya bila 3.1–3.4 sudah stabil dan masih ada waktu |

### Fase 4 — Pembekuan & dokumentasi (10–14 Nov)

| # | Langkah | Selesai bila |
|---|---|---|
| 4.1 | **Code freeze 14 Nov** — hanya perbaikan bug setelahnya | tag git `v1.0` |
| 4.2 | Uji reproduksi dari clone bersih + venv baru | hash SHA-256 CSV identik dengan yang akan dikirim |
| 4.3 | `technical_report.md` lengkap | memuat: pendekatan & alasannya; aset dipakai/dibuang; penanganan tracking hilang/berisik; aturan possession (bola lepas, duel, restart); keterbatasan; cara reproduksi |
| 4.4 | Cek kebocoran data di repo | tidak ada file data/derivatif; output notebook bersih |
| 4.5 | Repo dipublikasikan (public) | URL bisa dibuka tanpa login |

### Fase 5 — Kirim (15–16 Nov)

1. Bangun ulang CSV dari repo publik → `submissions/<nama_tim>.csv`.
2. `python evaluation/validate_submission.py submissions/<nama_tim>.csv` pada **file persis** yang diunggah.
3. Ekspor laporan → `<nama_tim>.pdf`.
4. Isi Google Form (butuh akun Google): nama tim, CSV, URL repo, PDF. Boleh diedit sampai deadline.

---

## 4. Pembagian peran (bila tim 3–5 orang)

| Peran | Tanggung jawab |
|---|---|
| **Bola mati** | Fase 1.3, 3.1, 3.2 |
| **Possession** | Fase 2.1–2.7 |
| **Validasi & reproduksi** | Fase 0, 3.3–3.4, 4.2, log eksperimen, penjaga aturan |
| **Dokumentasi** | `technical_report.md`, markdown notebook, README |
| (opsional) **Broadcast/video** | Fase 3.5–3.6 |

---

## 5. Protokol validasi (agar tidak "overfit" ke 5 menit)

Karena GT penuh privat dan GT publik terlalu kecil, setiap versi dinilai dengan **tiga lapis**:

1. **Kebenaran (GT publik):** lolos validator, frame selaras, label bermakna benar. Laporkan
   spellF1/macroF1 publik **dengan interval bootstrap** — tidak dipakai untuk memilih parameter
   kecuali selisihnya jauh melampaui interval.
2. **Proxy seluruh match (tanpa GT):**
   - kesepakatan tim possession dengan tag fase menyerang/bertahan Smart Tagging;
   - persentase restart (awal set piece) yang jatuh tepat di transisi D→hidup prediksi;
   - kesepakatan dengan pseudo-label "kontrol jelas" pada frame yang **disisihkan** dari pelatihan;
   - kewajaran statistik: jumlah possession, durasi rata-rata, porsi D, porsi H.
3. **Stabilitas:** hasil tidak berubah drastis bila parameter digeser ±20%.

Setiap eksperimen satu baris di `docs/experiment_log.md`:

| tanggal | versi | perubahan | spellF1 publik [interval] | macroF1 publik | proxy | #poss | keputusan |
|---|---|---|---|---|---|---|---|

---

## 6. Risiko & mitigasi

| Risiko | Mitigasi |
|---|---|
| Repo tidak bisa menghasilkan ulang file yang sama | pipeline hanya dari data mentah; uji clone bersih (4.2); tanpa artefak yatim di `cache/` |
| Tuning ke 5 menit publik | protokol §5; parameter dari prinsip + proxy |
| D palsu memecah possession | utamakan presisi D; segmen D minimum; decoder dengan biaya pergantian |
| Tim restart throw-in tidak diketahui | 3.2 dari geometri |
| Data bocor ke repo publik | `.gitignore` sejak 0.3; bersihkan output notebook; cek 4.4 |
| Data terkirim ke LLM cloud | notebook hanya cetak agregat; data mentah tidak dibuka di chat |
| Tim < 3 orang | tidak eligible untuk Innovation Challenge & Final Pitch → tuntaskan di 0.1 |
| Waktu habis untuk stretch goal | broadcast/video hanya setelah gerbang Fase 2 terpenuhi |

---

## 7. Progres

| Fase | Status | Catatan |
|---|---|---|
| Skrip uji coba lama (`.py`) | 🗑️ dihapus | pelajarannya tercatat di laporan `cache/*.txt` lama; dibangun ulang di Fase 1 |
| Fase 0 — Fondasi | ✅ 20 Okt (kecuali 0.1) | git + submodule resmi + nbstripout, `.venv` Py 3.11 dipin, `common.ipynb`, `00_setup_cek_data.ipynb` **35/35 PASS**, run_all, README, log, kerangka laporan. **0.1 nama & anggota tim masih terbuka** |
| Fase 1 — Bangun ulang + submission pertama | ✅ 20 Okt | 01 preprocess (regresi identik), 02 EDA GT publik (kesimpulan desain), 03 bola mati v3, 06 v0 → file valid, reproduksi hash identik dari nol (± 1 menit). Publik spellF1 0,344 [0,19–0,50] vs baseline 0,326. **Hambatan: presisi D (0,52)** |
| Fase 2 — Model possession v1 | ⬜ belum | |
| Fase 3 — Peningkatan | ⬜ belum | |
| Fase 4 — Pembekuan & dokumentasi | ⬜ belum | |
| Fase 5 — Kirim | ⬜ belum | |
