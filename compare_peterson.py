# -*- coding: utf-8 -*-
"""
Compare the FEA stress concentration factors with Peterson's formula and
plot the results.

Usage (normal Python 3, not Abaqus):
    pip install matplotlib
    python compare_peterson.py

Reference: Pilkey & Pilkey, Peterson's Stress Concentration Factors,
3rd ed., Wiley 2008, finite-width plate with a central circular hole in
uniaxial tension, net-section factor:
    Kt_n = 2 + 0.284 (1 - d/W) - 0.600 (1 - d/W)^2 + 1.32 (1 - d/W)^3
"""
import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(HERE, 'results')


def kt_peterson(d_over_w):
    x = 1.0 - d_over_w
    return 2.0 + 0.284 * x - 0.600 * x ** 2 + 1.32 * x ** 3


def read_csv(name):
    with open(os.path.join(RES, name)) as f:
        return [{k: float(v) for k, v in r.items()} for r in csv.DictReader(f)]


def main():
    rows = read_csv('results.csv')
    lines = ['| d/W | Kt FEA | Kt Peterson | Error |',
             '|---|---|---|---|']
    worst = 0.0
    for r in rows:
        ref = kt_peterson(r['d_over_W'])
        err = 100.0 * (r['Kt_net_FEA'] - ref) / ref
        worst = max(worst, abs(err))
        r['Kt_ref'] = ref
        lines.append('| %.2f | %.3f | %.3f | %+.2f %% |'
                     % (r['d_over_W'], r['Kt_net_FEA'], ref, err))
    lines.append('')
    lines.append('Largest error: %.2f %%' % worst)

    conv_path = os.path.join(RES, 'convergence.csv')
    conv = read_csv('convergence.csv') if os.path.exists(conv_path) else []
    if conv:
        lines += ['', '| Elements on hole arc | Elements | Kt FEA |',
                  '|---|---|---|']
        for c in conv:
            lines.append('| %d | %d | %.4f |'
                         % (c['arc_elements'], c['n_elements'],
                            c['Kt_net_FEA']))

    summary = '\n'.join(lines) + '\n'
    with open(os.path.join(RES, 'summary.md'), 'w') as f:
        f.write(summary)
    print(summary)

    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        print('matplotlib not installed: table written, no plot.')
        return

    xs = [i / 100.0 for i in range(5, 61)]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(xs, [kt_peterson(x) for x in xs], '-', color='#1f4e79',
            label="Peterson (Pilkey 2008)")
    ax.plot([r['d_over_W'] for r in rows], [r['Kt_net_FEA'] for r in rows],
            'o', color='#c0392b', markersize=7, label='Abaqus, CPS8R')
    ax.set_xlabel('d / W')
    ax.set_ylabel('Kt (net section)')
    ax.set_title('Plate with a central hole in tension')
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(RES, 'kt_vs_dW.png'), dpi=150)
    print('Plot written: results/kt_vs_dW.png')


if __name__ == '__main__':
    main()
