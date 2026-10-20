# More than a Hack 2027 — Ball Possession · solusi tim `NAMA_TIM`

Solusi untuk [More than a Hack 2027, Phase 1](https://github.com/metrica-sports/more-than-a-hack-2027):
memberi label `H` / `A` / `D` / `X` pada setiap 199.319 frame video tactical FC Barcelona – Athletic Club.

Seluruh pipeline ditulis sebagai **Jupyter notebook** berurutan, dengan penjelasan markdown di setiap langkah.
Rencana kerja dan status ada di [docs/RENCANA.md](docs/RENCANA.md); catatan eksperimen di
[docs/experiment_log.md](docs/experiment_log.md); dokumen teknis di [docs/technical_report.md](docs/technical_report.md).

> **Data pertandingan tidak ada di repo ini** dan tidak boleh di-commit — lisensinya khusus lomba.

## Struktur

```
notebooks/
  common.ipynb               konstanta & fungsi bersama (dimuat lewat %run, tidak dijalankan sendiri)
  00_setup_cek_data.ipynb    cek lingkungan, kelengkapan & keselarasan data, uji asap scorer
  ...                        tahap berikutnya ditambahkan per fase (lihat docs/RENCANA.md)
docs/                        rencana, log eksperimen, dokumen teknis
external/more-than-a-hack-2027/   repo resmi (git submodule): games.py, scorer, GT publik 5 menit
run_all.ps1 / run_all.sh     menjalankan semua notebook berurutan
requirements.txt             dependensi langsung (dipin)
requirements-lock.txt        kunci lengkap pip freeze
```

Dibuat saat dijalankan (gitignored): `cache/` (artefak antara + `cache/reports/` laporan agregat tiap notebook)
dan `submissions/` (file CSV).

## Instalasi

Python **3.11**.

```bash
git clone --recurse-submodules <url-repo-ini>
cd <repo>
py -3.11 -m venv .venv                                     # macOS/Linux: python3.11 -m venv .venv
.venv\Scripts\python -m pip install -r requirements-lock.txt
.venv\Scripts\nbstripout --install --attributes .gitattributes   # hanya untuk kontributor
```

`nbstripout` membersihkan output notebook secara otomatis saat commit, supaya tidak ada angka atau plot turunan
data yang ikut terpublikasi. Output tetap ada di salinan lokal.

## Data

Unduh paket data (lihat [DATA.md resmi](external/more-than-a-hack-2027/DATA.md)) dan letakkan di akar repo:

```
tactical/   BAR-ATH_tactical_atd.xml, _atd.txt, _homography.csv, _smart_tagging.xml  (video opsional)
broadcast/  BAR-ATH_broadcast_atd.xml, _atd.txt, _homography.csv  (video opsional)
```

Atau taruh di tempat lain dan arahkan `MTAH_DATA_DIR` ke folder yang berisi `tactical/` dan `broadcast/`.

## Reproduksi

```powershell
powershell -ExecutionPolicy Bypass -File run_all.ps1
```

```bash
./run_all.sh
```

Setiap notebook diakhiri cek otomatis; run berhenti di notebook pertama yang gagal. Mulai dari tengah:
`run_all.ps1 -From 03` atau `./run_all.sh 03`.

## Tim

`NAMA_TIM` — anggota: _(diisi)_
