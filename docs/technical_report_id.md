# Ball possession dari tracking otomatis — dokumen teknis

**Tim:** Més Que Un Data — Raya Ramadha Fitroh, Fauzan Ahsanudin Alfikri, Gabriel Edbert Liandrew, Benedict Brian Joel Purba, Yan Ardhinaya Ardika · **Repo:** _(URL publik)_ · **File:** _(nama final ditetapkan di Fase 5)_ · **SHA-256 CSV:** _(diisi saat submit)_

> **Salinan kerja berbahasa Indonesia** — versi yang dikirim: `technical_report.md` (bahasa Inggris); isi harus tetap sama.
>
> **Status: draf (21 Okt 2026), versi pipeline v4.** Struktur mengikuti SUBMISSION.md. Difinalkan di Fase 4.3 lalu
> diekspor ke PDF bernama tim. Hanya angka agregat — tidak ada data per frame di dokumen ini. Angka GT publik selalu
> dari 5 menit pertama (17 possession) dan hanya untuk cek kebenaran.

## 1. Ringkasan

Kami memisahkan masalah menjadi dua keputusan yang masing-masing diselesaikan sebagai **segmentasi**, bukan
klasifikasi per frame: (1) **bola hidup atau mati**, dengan fitur kolektif pemain dan bola, siaran broadcast sebagai saksi kedua, "jangkar" bukti yang
hampir pasti, dan Viterbi dua keadaan; (2) **tim mana yang menguasai bola**, dengan model logistik atas **bentuk tim**
(lebar, sebaran, kecepatan relatif) yang dilatih dari *pseudo-label* "kontrol jelas" di seluruh pertandingan — tanpa
ground truth — sehingga bekerja juga pada ± 41% frame dinilai saat bola tidak terlihat. Keduanya digabung oleh
Viterbi tiga keadaan (H/A/D) dengan biaya pergantian dalam "detik bukti". Pada GT publik, versi v3 mencapai
**spellF1 ± 0,67 [0,44 – 0,83]** (baseline resmi ± 0,33 [0,21 – 0,45]) dan macroF1 ± 0,89. Rekaman broadcast yang tidak
sinkron diselaraskan ke timeline tactical hanya lewat posisi pemain. Seluruh pipeline adalah
notebook Jupyter yang dijalankan berurutan oleh satu perintah dan menghasilkan file yang identik byte demi byte.

## 2. Pendekatan & alasannya

**Metrik membentuk desain.** spellF1 menghitung setiap possession sekali. Dua kesalahan termahal adalah
*pergantian palsu* (`H H A H H` memecah satu possession menjadi tiga) dan *bola mati palsu* di tengah possession
(`H D H`). Karena itu setiap komponen menghasilkan **segmen** dan lebih "enggan" berganti keadaan daripada mengejar
akurasi per frame.

**Arsitektur.**

```
ATD + Smart Tagging ─► 01 preprocess ─► 03 bola mati (hidup/mati + restart) ─┐
                                    └─► 04 fitur ─► 05 model bentuk tim ─────┴─► 06 decoder H/A/D ─► CSV
```

| Tahap | Inti |
|---|---|
| `01` broadcast | penyelarasan broadcast ↔ tactical lewat posisi pemain (offset tetap per babak); bola broadcast mengisi celah bola tactical; jenis gambar siaran per frame (lapangan / replay atau close-up) |
| `03` bola mati | 7 fitur kolektif (pemain tenang relatif norma lokal, tidak ada operan, celah bola, bola dekat garis, **siaran menayangkan replay/close-up**, bola pelan, jendela set piece) dengan bobot dari prinsip; **jangkar** ±3 per frame: perebutan bola → hidup, bola ≥ 1 m di luar garis selama ≥ 1 s → mati, celah bola ≥ 10 s → mati; Viterbi 2 keadaan (biaya pergantian 20, segmen minimum 2 s); bias dipilih agar porsi `D` = prior **0,48**; segmen `D` wajib memuat ≥ 1 isyarat henti |
| `04`–`05` tim | pseudo-label "kontrol jelas" (pemain ≤ 1,5 m dari bola teramati, lawan ≥ 3 m, ≥ 0,5 s) → logistik (IRLS + L2) atas 6 selisih bentuk tim H − A yang dihaluskan ± 2 s; prediksi *out-of-fold* per blok waktu; ditambah β × "tim terdekat ke bola" dengan β ≈ 1,0 ditaksir tanpa GT |
| `06` decoder | Viterbi H/A/D per babak; `D` dari tahap 03; pergantian H↔A membayar 1 s × median \|log-odds\|; 2 s pertama setelah sepak pojok/tendangan gawang/tendangan bebas diberikan ke tim pengambil |

**Mengapa bukan model terlatih pada GT?** GT publik hanya 17 possession dan 4 segmen bola mati — terlalu kecil
untuk melatih, dan EVALUATION.md menunjukkan bahkan satu hiperparameter yang dipilih di sana bisa salah. Kami
memakainya hanya untuk memahami definisi (`02`) dan memeriksa kebenaran. Semua parameter berasal dari prinsip
sepak bola/fisika atau dari data pertandingan sendiri (pseudo-label, jangkar, proxy).

## 3. Aset yang dipakai & yang dibuang

| Aset | Dipakai? | Untuk apa / mengapa tidak |
|---|---|---|
| ATD tactical | **ya** — sumber utama | posisi & kecepatan pemain per slot, posisi bola; tim per slot dari XML |
| Smart Tagging | **sebagian** | jendela & awal `SET PIECES` (fitur lemah + isyarat henti), `Kick Off (After Goal)` (aturan pasti), `Team` sepak pojok/tendangan gawang/tendangan bebas = **tim pengambil** (diverifikasi geometri: sepak pojok 12/12 di separuh lawan tim tag). Tag fase (Build Up, Defending…) **tidak** dipakai: di jendela publik hanya cocok 60–76% dengan possession — fase bukan possession |
| Homography tactical | tidak | ATD sudah dalam koordinat lapangan; dicek valid 100% |
| ATD + homography broadcast | **ya** | diselaraskan lewat posisi pemain (offset tetap per babak ± 160,6 s dan ± 1076,8 s, drift dapat diabaikan; pemain cocok ± 0,75 m, bola ± 0,8 m). Dipakai untuk: (1) bola broadcast mengisi celah tactical (bola tersedia 59% → ± 63% frame dinilai; 39% frame hidup tanpa bola tactical tertolong); (2) jenis gambar siaran — saat replay/close-up (homografi tidak valid, 33% frame dinilai) pemain bergerak seperti bola mati (± 1,0 vs ± 2,1 m/s) → bukti bola mati |
| Video tactical / broadcast | tidak | — |
| GT publik 5 menit | hanya cek | memahami definisi `D` & pergantian (`02`); skor dengan interval bootstrap sebagai cek kebenaran |
| Pengetahuan eksternal | ya | porsi bola mati ≈ 0,48 dari waktu bermain efektif LaLiga yang umum (± 50–56 menit dari ± 95–100) |

## 4. Penanganan tracking yang hilang & berisik

- **Bola hilang 41% frame dinilai, hampir seluruhnya dalam celah panjang** (150 celah, median ± 11 s; celah ≤ 1 s
  hanya 0,1% frame hilang). Interpolasi linear hanya untuk celah ≤ 1 s yang fisik masuk akal (41 frame).
  Akibatnya possession harus disimpulkan dari pemain: model bentuk tim memberi akurasi tim ± 0,92 di GT publik,
  **termasuk saat bola tidak terlihat**.
- **Celah bola panjang adalah bukti bola mati.** Ditunjukkan tanpa GT: di celah ≥ 10 s kecepatan median pemain
  0,8–1,1 m/s, lebih lambat dari kelompok yang pasti mati (sebelum kick-off 1,3; bola keluar 1,5) dan jauh dari
  perebutan bola (2,3). Ada ± 79 celah semacam itu.
- **Slot tanpa identitas, duplikat, hilang.** Semua fitur bersifat kolektif per tim (rentang, varians, rata-rata),
  tidak per pemain; fitur bentuk = `NaN` bila tim terlacak < 6 slot (± 6% frame). Kecepatan per slot dibatasi 12 m/s
  untuk membuang lompatan identitas.
- **Lompatan posisi bola** (> 3 m/frame, 13 frame dinilai) hanya ditandai; fitur bola dihaluskan dengan median.
- **Arah serang** dibaca dari XML lalu diverifikasi dengan posisi pemain sebelum kedua kick-off.

## 5. Aturan possession yang diterapkan

- **Bola mati (`D`)**: segmen dari detektor `03`. Dipaksa `D`: babak 2 sebelum kick-off (FAQ.md) dan jendela sebelum
  kick-off setelah gol. Segmen < 2 s dan segmen tanpa isyarat henti (celah bola, bola keluar, bola diletakkan, awal
  tag set piece) dibuang.
- **Pergantian possession "terkontrol"**: tim baru harus mengumpulkan bukti bersih setara ± 1 s bukti biasa
  (biaya Viterbi). Sentuhan sesaat tidak cukup.
- **Bola lepas, duel, defleksi**: frame tanpa bola atau dengan bukti seimbang tidak menggeser keputusan, sehingga
  possession tetap milik tim terakhir — sesuai CHALLENGE.md. Analisis `02` mendukung ini: pada sebagian besar
  pergantian di GT publik tim baru sudah paling dekat ke bola 1–3 s *sebelum* GT berganti.
- **Restart**: 2 s pertama setelah sepak pojok, tendangan gawang, dan tendangan bebas = tim pengambil (tag).
  Lemparan ke dalam tidak punya tim di tag; possession-nya diputuskan decoder dari bukti biasa.
- **`X`**: tidak dipakai pada frame dinilai (decoder selalu memutuskan); hanya pada frame tidak dinilai.

## 6. Validasi

**Protokol.** (1) GT publik hanya cek kebenaran, dengan interval bootstrap resmi; (2) proxy tanpa GT di seluruh
pertandingan; (3) stabilitas — parameter dipilih di dataran, bukan di puncak tajam. Perubahan diadopsi hanya bila
proxy membaik dan GT publik tidak memburuk. Semua eksperimen tercatat di `docs/experiment_log.md`.

**Perkembangan versi (GT publik).**

| Versi | Perubahan | spellF1 [5–95%] | macroF1 | akurasi tim (frame hidup) |
|---|---|---|---|---|
| baseline resmi | tim terdekat + voting ± 50 | 0,33 [0,21 – 0,45] | 0,62 | 0,83 |
| v0 | detektor `D` v3 + Viterbi atas tim terdekat | 0,34 [0,19 – 0,50] | 0,72 | 0,69 |
| v1 | + model bentuk tim | 0,54 [0,32 – 0,74] | 0,77 | 0,75 |
| v2 | + jangkar & aktivitas operan di `D` | 0,59 [0,37 – 0,77] | 0,86 | 0,89 |
| v3 | + syarat isyarat henti, prior restart | 0,64 [0,40 – 0,81] | 0,87 | 0,90 |
| **v4** | + broadcast: bola mengisi celah, replay/close-up sebagai bukti bola mati | **0,67 [0,44 – 0,83]** | **0,89** | **0,90** |

**Detektor bola mati — ablation dengan proxy tanpa GT** (porsi `D` sama).

| Varian | perebutan dicap `D` | bola keluar dicap `D` | celah ≥ 10 s dicap `D` | publik presisi / recall |
|---|---|---|---|---|
| fitur saja | 20% | 85% | 79% | 0,52 / 0,91 |
| + jangkar + operan | 0,7% | 96% | 100% | 0,80 / 0,81 |
| + syarat isyarat henti | 1,3% | 97,5% | 100% | 0,85 / 0,81 |
| + bola & fitur replay/close-up broadcast (final) | 1,0% | 96,9% | 100% | 0,86 / 0,86 |

**Model bentuk tim.** Validasi silang per blok waktu pada pseudo-label yang disisihkan: AUC ± 0,91 (blok terburuk
± 0,82). Keandalan "tim terdekat" ditaksir tanpa GT (q ± 0,73) dan cocok dengan yang terlihat di GT publik (± 74%).

**Eksperimen yang ditolak** (`07`): jangkar "kontrol jelas" di decoder (lebih banyak possession, tidak lebih baik),
menggeser batas ke sentuhan/kontrol pertama (batas kami tidak bias sistematis; publik turun), dan mengoreksi
keterlambatan bukti bentuk tim (terukur ± 4 s tanpa GT, tetapi koreksinya memperburuk).

**Sensitivitas.** Skor publik identik untuk biaya pergantian 0,25–1,5 s; proxy bola mati stabil untuk prior porsi
`D` 0,45–0,48 dan memburuk mulai 0,51; kekuatan jangkar 1–6 dan biaya Viterbi bola mati 10–40 tidak mengubah gambaran.

## 7. Keterbatasan & yang akan diperbaiki dengan waktu lebih

- **Possession sangat pendek** (≤ 1–2 s) hampir tanpa bukti di tracking otomatis dan tidak tertangkap; di GT publik
  3 dari 17 possession seperti ini.
- **Bukti bentuk tim tertinggal ± 4 s** setelah bola berpindah; possession pendek 3–8 s sering tergabung.
- **Bola mati pendek dengan bola tak terlihat** (mis. lemparan ke dalam cepat) dapat terlewat; celah bola 3–10 s
  bercampur hidup/mati.
- **Porsi bola mati bergantung pada prior** dari pengetahuan umum (0,48).
- **Tim pengambil lemparan ke dalam** tidak diketahui dari tag.
- Arah lanjutan: deteksi bola dari video/broadcast untuk mengisi celah; model durasi (HSMM); sinyal waktu
  pergantian yang lebih tajam dari bola.

## 8. Reproduksi

```bash
git clone --recurse-submodules <repo>
py -3.11 -m venv .venv
.venv\Scripts\python -m pip install -r requirements-lock.txt
powershell -ExecutionPolicy Bypass -File run_all.ps1      # → submissions/MesQueUnData_<versi>.csv
```

Data diletakkan di `tactical/` dan `broadcast/` di akar repo (atau `MTAH_DATA_DIR`). Notebook `00` memverifikasi
data dan lingkungan (35 cek). Diukur pada clone bersih dengan venv baru (21 Okt 2026): instalasi ± 2,5 menit, seluruh pipeline (notebook 00–07)
± 3,5 menit di CPU laptop. Hash SHA-256 CSV yang dihasilkan harus sama dengan yang tertulis di atas; untuk versi v4:
`627a5cc0d79798dc70db0d3087cfdb13c889dc8d08131eea306425c08de56afe`.
