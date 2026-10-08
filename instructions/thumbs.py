"""Quick part thumbnails (matplotlib) with the LDraw axes drawn, to check a part's shape and frame.
usage: python instructions/thumbs.py out.png 23443 48729b ..."""
import os, sys, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'pipeline'))
import ldraw
out, ids = sys.argv[1], sys.argv[2:]
n = len(ids); cols = min(n, 6); rows = (n + cols - 1) // cols
fig = plt.figure(figsize=(3 * cols, 3 * rows))
L = np.array([0.45, -0.8, 0.4]); L /= np.linalg.norm(L)
for k, pid in enumerate(ids):
    ax = fig.add_subplot(rows, cols, k + 1, projection='3d')
    V, C = ldraw.tris(pid + '.dat')
    W = V[:, :, [0, 2, 1]] * np.array([1, 1, -1])            # LDraw (x, y down, z) -> plot (x, z, -y)
    nrm = np.cross(W[:, 1] - W[:, 0], W[:, 2] - W[:, 0]); nl = np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-9
    sh = 0.35 + 0.65 * np.abs((nrm / nl) @ np.array([0.45, 0.4, 0.8]))
    pc = Poly3DCollection(W, facecolors=np.c_[sh * .85, sh * .7, sh * .55], edgecolors='none'); ax.add_collection3d(pc)
    P = W.reshape(-1, 3); c = (P.max(0) + P.min(0)) / 2; r = (P.max(0) - P.min(0)).max() / 2 + 2
    ax.set_xlim(c[0] - r, c[0] + r); ax.set_ylim(c[1] - r, c[1] + r); ax.set_zlim(c[2] - r, c[2] + r)
    for d, col, lab in (((r, 0, 0), 'r', 'x'), ((0, r, 0), 'b', 'z'), ((0, 0, r), 'g', '-y')):
        ax.plot([0, d[0]], [0, d[1]], [0, d[2]], col, lw=2); ax.text(*d, lab, color=col)
    ax.set_title(pid + '  ' + str(np.round(V.reshape(-1, 3).min(0))) + '..' + str(np.round(V.reshape(-1, 3).max(0))), fontsize=7)
    ax.view_init(22, -60); ax.set_axis_off()
plt.tight_layout(); plt.savefig(out, dpi=80)
