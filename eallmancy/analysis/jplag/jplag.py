import sys
sys.path.insert(0,'/root/eallmancy')

from pathlib import Path
import shutil
import os
from glob import glob

import subprocess
from typing import List

import pandas as pd
import polars as pl


def _get_code(art):
    return '\n'.join(art.solution_part_strs)

jplag_root = Path(__file__).parent.resolve()
inp_pth = Path('.jplag_inp')
out_pth = Path('.jplag_otp')

def clean_jplag_dirs():
    # clear everything and rewrite
    if inp_pth.exists():
        shutil.rmtree(str(inp_pth))
    inp_pth.mkdir(exist_ok=True)

    if out_pth.exists():
        shutil.rmtree(str(out_pth))
    out_pth.mkdir(exist_ok=True)
    for f in glob(f'./{out_pth}*.jplag'):
        os.remove(f)

def prepare_jplag_dirs(trace):
    # write out filenames as {IDX}.py
    for art_id, art in trace.graph.nodes(data='artifact'):
        with open(str(inp_pth / f'{art_id}.py'), 'w') as f:
            f.write(_get_code(art))

def run_jplag():
    cmd = [
        "java", "-jar", str(jplag_root / "jplag.jar"),  # Use the actual path to your JPlag jar
        "-l", "python3",     # Language
        str(inp_pth),        # Submissions path
        "-r", str(out_pth),  # Output directory
        "--csv-export",
        "--min-tokens=6",
        "--mode=RUN"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result

def sort_cols(df):
    sorted_cols = ['n'] + list(sorted([c for c in df.columns if c!='n' and c!='m'], key=lambda s: int(s)))
    return df.select(sorted_cols)

def scrape_stats():
    stats = (
        pd.read_csv(str(out_pth / 'results.csv'))
        .pipe(pl.from_pandas)
        .with_columns(
            pl.col.submissionName1.str.replace(".py","").cast(int),
            pl.col.submissionName2.str.replace(".py","").cast(int),
        )
        .with_columns(
            pl.min_horizontal(["submissionName1", "submissionName2"]).alias("n"),
            pl.max_horizontal(["submissionName1", "submissionName2"]).alias("m"),
        )
        .select("n", "m", "averageSimilarity", "maxSimilarity")
    )
    
    stats_matrix = (
        stats
        .pivot(on='m', index='n', values='maxSimilarity')
        .pipe(sort_cols)
        .sort(pl.col('n'))
        .to_numpy()[:,1:]
    )
    
    stats_dict = {(n,m): {'avg': avgsim, 'max': maxsim} for (n, m, avgsim, maxsim) in stats.rows()}
    return stats, stats_matrix, stats_dict

def calc_jplag_distances(trace, verbose=False):
    clean_jplag_dirs()
    prepare_jplag_dirs(trace)
    resp = run_jplag()

    if resp.returncode != 0:
        raise Exception(resp.stderr)

    res = scrape_stats()
    if not verbose:
        return res
    else:
        return res, resp.stdout, resp.stderr
