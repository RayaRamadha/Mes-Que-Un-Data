# Log eksperimen

Satu baris per eksperimen, terbaru di bawah. Protokol penilaian ada di [RENCANA.md §5](RENCANA.md#5-protokol-validasi-agar-tidak-overfit-ke-5-menit).

- **spellF1 / macroF1 publik** = skor terhadap GT publik 5 menit (17 possession). Hanya untuk cek kebenaran,
  bukan untuk memilih versi; satu possession ≈ ±6 poin spellF1. Tulis interval bootstrap bila ada.
- **proxy** = metrik seluruh match tanpa GT (kesepakatan dengan Smart Tagging, restart, pseudo-label tersisih).
- **#poss / durasi** = jumlah possession dan durasi rata-rata yang dilaporkan file (seluruh match).
- **keputusan** = dipakai / dibuang / perlu diselidiki, dan alasannya.

| # | tanggal | notebook / versi | perubahan | spellF1 publik [interval] | macroF1 publik | proxy | #poss / durasi | keputusan |
|---|---|---|---|---|---|---|---|---|
| 0 | 2026-10-20 | baseline resmi `baseline_smooth50` | acuan: pemain terdekat ke bola + voting mayoritas ±50 frame | 0.3256 | 0.6207 | – | – | acuan; full match resmi spellF1 **0.2433** (batas bawah) |
| 1 | 2026-10-20 | `06` v0 (`03` v3) | D: fitur kolektif + Viterbi 2 keadaan, bias dari prior porsi D 0,48; H/A: Viterbi 3 keadaan atas tim terdekat, `SWITCH_HA`=25 | 0.3444 [0.189 – 0.501] | 0.7249 | – | 302 / 11,0 s | **acuan Fase 1**. Tidak beda nyata dari baseline (interval). Akurasi tim frame hidup 0,69 vs baseline 0,83 karena D palsu (presisi D publik 0,52) → prioritas presisi D. sha256 `e04dcc07…` (reproduksi identik) |
| 2 | 2026-10-20 | `06` v1 (`04` + `05`, `03` v3) | H/A dari log-odds model bentuk tim (logistik pada pseudo-label "kontrol jelas" seluruh match, out-of-fold per blok) + β·tim terdekat (β≈1,0 ditaksir tanpa GT); `SWITCH_S`=1 s bukti | **0.5379 [0.317 – 0.745]** | 0.7717 | pseudo cocok 91,2% · restart cocok 84,1% · porsi H hidup 0,54 | 187 / 17,7 s | **acuan baru**. Skor publik datar untuk SWITCH_S 0,25–1,5 s. 12 vs 17 possession publik (possession pendek terlewat). Akurasi tim frame hidup 0,75 vs model bentuk 0,92 → D palsu masih hambatan → 3.1, lalu 2.7. sha256 `84c06ef6…` |
