import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.text import Text

fig, ax = plt.subplots(figsize=(10, 10))
ax.set_ylabel('Energy (J)')
ax.set_xlabel('Nb deps')
width = 0.4
nbs = [
    [7, 5, 8],
    [1, 2, 4],
    [7, 5, 8],
    [1, 2, 4],
    [7, 5, 8],
    [1, 2, 4],
]
patterns = ["/", "/" , "o", "o", "\\", "\\"]
colors = ["#6495ed", "#EDC88B", "#6495ed", "#EDC88B", "#6495ed", "#EDC88B"]
labels = ["1\nmin", "1\nmin", "2\nmin", "2\nmin", "3\nmin", "3\nmin"]
x = np.arange(3) * 3
for i in range(6):
    b = ax.bar(x + width*i, nbs[i], width, bottom=[0, 0, 0], yerr=1, color=colors[i], label=labels[i])
    ax.bar_label(b, labels=[labels[i]]*3, padding=3, label_type="center", weight="bold")

legend_els = [Patch(facecolor="#6495ed", label="direct"), Patch(facecolor="#EDC88B", label="rn")]
# ax.legend(loc='upper left', ncols=3, borderaxespad=0.)
ax.legend(handles=legend_els, loc="upper left")
ax.set_xticks(x, [5, 15, 30])
# ax.annotate("label1", (0,0), xytext=(20, 20), size=15)
plt.show()
