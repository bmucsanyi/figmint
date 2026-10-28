# Legend placement

Both backends place a legend by the same rule: the legend sits flush at one of nine anchors of the axes, with the column count that covers the least plotted ink. `figmint.sty` applies the rule at `\end{axis}`, and `legend(axis, ...)` applies it in matplotlib. The two implementations run the same fixtures in `tests/fixtures/legend`.

## Candidates

The anchors are the four corners of the axes, the middles of its four edges, and its center. A legend at an anchor sits flush with the axes frame: at a corner it touches both edges, and at the middle of an edge it touches that edge and is centered along it. In matplotlib, a legend with a visible frame stays inside by half its frame line width.

With $n$ legend entries, a candidate is an anchor and a column count $C \in \{1, \ldots, n\}$. Under `loc="best"` and `figmint legend best`, every anchor is a candidate; under a fixed location, only that anchor is. The size of each candidate is the size of the real legend at $C$ columns, typeset or rendered by the backend. A candidate whose legend is wider or taller than the axes is dropped, and when no candidate remains, placement fails with an error.

## Ink

The axes are divided into square cells of side $c = 2\,\mathrm{pt}$, indexed by column $i$ from the left and row $j$ from the bottom. Ink occupies cells as follows:

- A stroked segment occupies the cells that contain its points sampled at steps of at most $c/2$ along both axes. A curve contributes the segments of its control polygon.
- A filled path occupies its boundary, as above, and every cell whose center lies inside the path under the even-odd rule.
- A text annotation, an image, and a shaded surface occupy every cell that their bounding box overlaps.

Ink is what the plots and the annotations inside the axes draw. In PGFPlots, that is everything drawn after the axis background, grid, and the axis lines below the plots, including the markers that PGFPlots draws after the axis. In matplotlib, it is every child of the axes except the background, spines, axes, titles, and the legend.

## Score

Let a candidate legend of width $w$ and height $h$ overlap columns $i_0, \ldots, i_1$ and rows $j_0, \ldots, j_1$ of axes with width $W$ and height $H$, and let $R = \lceil n / C \rceil$ be its number of rows. Candidates are compared by the following scores, in this order:

1. The badness $b$, the number of occupied cells that the legend overlaps. Smaller is better.
2. The number of empty legend cells, $C R - n$. Smaller is better.
3. The balance $|C - R|$. Smaller is better.
4. For $b = 0$, the clearance, the squared distance in cells from the legend to the nearest ink, $$\min_{(i, j)\ \text{occupied}} \left(\max(0, i - i_1, i_0 - i)^2 + \max(0, j - j_1, j_0 - j)^2\right),$$ which is unbounded when no cell is occupied. Larger is better.
5. For $b = 0$, the margin, the largest factor $s \in \{t / 256 : t \in \mathbb{N}\}$ by which the legend can grow about its anchor point, clipped to the axes, while it overlaps no occupied cell. The margin is unbounded when the legend can grow to cover the axes. Larger is better.
6. The anchor complexity: 0 for the corners and the middles of the top and bottom edges, 1 for the middles of the left and right edges, 2 for the center. Smaller is better.
7. The size $w / W + h / H$. Smaller is better.
8. The anchor rank, in the order upper right, upper left, lower left, lower right, right, left, lower center, upper center, center. Earlier is better.
9. The column count $C$. Smaller is better.

## Cost

In PGFPlots, ink is collected only for an axis whose legend figmint places, while PGFPlots draws it, at a cost linear in what is drawn. Other axes are not touched, so they keep the Lua backend of PGFPlots. Each candidate then costs a constant number of lookups in a summed-area table of the grid and one pass over its rows for the clearance. In matplotlib, `legend` draws the figure once, whatever the number of legend entries.
