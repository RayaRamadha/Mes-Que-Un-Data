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
