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
