# Normal color cycle

The `normal` color cycle is a constrained repair of the Catppuccin Latte cycle for white-background academic figures. The Catppuccin Latte cycle is the starting point and the repaired cycle stays in the same order.

Let $p_i$ be the original Latte color at cycle index $i$ and $c_i$ be the repaired color at the same index. Colors live on the 8-bit sRGB grid, so each channel is an integer in $\{0,\ldots,255\}$. The first objective is to maximize the unchanged prefix length $k(c)=\max\{r:c_i=p_i\text{ for every }i<r\}$. Among palettes with maximal $k$, the second objective is lexicographic movement by cycle position: $$\operatorname{lexmin}_{c_0,\ldots,c_{n-1}}\left(\Delta E_{00}(c_k,p_k)^2,\Delta E_{00}(c_{k+1},p_{k+1})^2,\ldots,\Delta E_{00}(c_{n-1},p_{n-1})^2\right)$$

## Constraints

- Fixed ordering: color $c_i$ stays at Latte cycle position $i$.
- Exact preservation when possible: $c_i = p_i$ unless moving it is needed for a constraint.
- White-background contrast: $C(c_i,\mathrm{white}) \ge 3.0$ for every repaired color, using WCAG relative-luminance contrast.
- Categorical separation: $D(c_i,c_j) \ge 10$ for every distinct pair $i \neq j$.

The pairwise distance is the smallest CIEDE2000 distance over normal vision and three simulated color-vision modes: $$D(c_i,c_j)=\min_{m \in \{\mathrm{normal},\mathrm{protan},\mathrm{deutan},\mathrm{tritan}\}}\Delta E_{00}(S_m(c_i),S_m(c_j))$$

Here $S_m$ is the identity transform for normal vision and a severity-100 linear-RGB color-vision simulation for the other modes, clipped back into displayable sRGB before converting to CIELAB. The threshold $10$ is the default categorical color-blind-friendly `min_dist` bar used by `cols4all`.

## What the objective encodes

The first few colors appear most often, so they get first claim on staying close to Catppuccin Latte. Later colors are still constrained by contrast and color-vision separation, but they are allowed to move more when that protects earlier entries.

The one-time computation used the constraints above as an 8-bit sRGB constrained search and ranked feasible candidates by the objective above. The original `peach` fails the white-background contrast threshold, so the longest feasible unchanged prefix is one color. The shipped `normal` cycle keeps `blue` exactly, repairs `peach` first, and lets later entries carry the remaining pairwise-separation requirements. The test suite verifies the constraints above and checks the unchanged-prefix bound.

## Why no grayscale constraint

Grayscale separation is excluded from the constraints. The target medium is digital color academic figures, and in 2026 that is the main reading path. A grayscale constraint forces the palette to spend contrast budget on luminance ordering, which fights the color-vision constraints and makes the colors worse for the default use case. For black-and-white output, the right mechanism is redundant encoding: markers, line styles, hatches, direct labels, or separate figure variants.

## Sources

- The separation criterion follows the categorical `min_dist` check in [`cols4all`](https://cols4all.github.io/cols4all-R/articles/01_paper.html).
- The white-background contrast constraint follows the [WCAG non-text contrast](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html) threshold for graphical objects.
- The broader goals follow scientific-colormap guidance from [Crameri et al.](https://www.nature.com/articles/s41467-020-19160-7): perceptual separation, color-vision robustness, and readable scientific figures.

## Themed cycles

The formal repair above applies only to `normal`. The Catppuccin colors used by the themed styles are official palette values. Each themed style sets the line and bar color cycle from that theme and uses matplotlib's built-in `plasma` colormap for scalar data. Dark themes set the axes, figure, and saved-output background to the theme base color, so exported plots can be imported into matching slide decks without a white rectangle.
