# -*- coding: utf-8 -*-
"""
Run the parametric study and the mesh convergence check.

Usage (from this folder):
    abaqus cae noGUI=run_study.py

Abaqus job files (.odb, .inp, .msg, ...) go to the runs/ folder.
Writes results/results.csv and results/convergence.csv.
"""
from __future__ import print_function

import csv
import json
import os
import sys

HERE = os.getcwd()
RUNS = os.path.join(HERE, 'runs')
RESULTS = os.path.join(HERE, 'results')
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True

import plate_model  # noqa: E402

with open(os.path.join(HERE, 'params.json')) as f:
    P = json.load(f)

W, L, t = P['W'], P['L'], P['t']
E, nu, sigma = P['E'], P['nu'], P['sigma']
global_size = P['global_size_over_W'] * W
for folder in (RUNS, RESULTS):
    if not os.path.isdir(folder):
        os.makedirs(folder)
# Abaqus writes the job files in the current folder
os.chdir(RUNS)


def one_case(tag, d_over_w, arc_elements):
    d = d_over_w * W
    name = 'plate_%s' % tag
    plate_model.build_model(name, W, L, t, d, E, nu, sigma,
                            arc_elements, global_size)
    odb_path = plate_model.run_job(name, name)
    s22, n_elem = plate_model.peak_stress(odb_path)
    sigma_net = sigma * W / (W - d)
    row = {
        'd_over_W': d_over_w,
        'd_mm': d,
        'arc_elements': arc_elements,
        'n_elements': n_elem,
        'S22_max_MPa': round(s22, 3),
        'sigma_net_MPa': round(sigma_net, 3),
        'Kt_net_FEA': round(s22 / sigma_net, 4),
        'Kt_gross_FEA': round(s22 / sigma, 4),
    }
    print('%s  d/W=%.2f  Kt_net=%.4f' % (name, d_over_w, row['Kt_net_FEA']))
    return row


def write_csv(path, rows):
    keys = list(rows[0].keys())
    with open(path, 'w') as f:
        w = csv.DictWriter(f, fieldnames=keys, lineterminator='\n')
        w.writeheader()
        for r in rows:
            w.writerow(r)


# 1. Parametric study over d/W
rows = []
for dw in P['d_over_W']:
    rows.append(one_case('dw%02d' % int(round(dw * 100)), dw,
                         P['arc_elements']))
write_csv(os.path.join(RESULTS, 'results.csv'), rows)

# 2. Mesh convergence on one geometry
conv = []
for n in P['convergence_arc_elements']:
    conv.append(one_case('conv%03d' % n, P['convergence_d_over_W'], n))
write_csv(os.path.join(RESULTS, 'convergence.csv'), conv)

print('Done. Now run: python compare_peterson.py')
