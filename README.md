# figmint

`figmint` is my Matplotlib style collection. I use it to create plots for papers, talks, and meetings.

## Preview

`normal`

![figmint normal style preview](gallery/theme_normal.png)

`latte`

![figmint latte style preview](gallery/theme_latte.png)

`frappe`

![figmint frappe style preview](gallery/theme_frappe.png)

`macchiato`

![figmint macchiato style preview](gallery/theme_macchiato.png)

`mocha`

![figmint mocha style preview](gallery/theme_mocha.png)

`frappe` with overrides

![figmint frappe override style preview](gallery/talk_frappe_overrides.png)

## API

`figmint` deliberately has a small API, making it easy to grasp:

```python
from figmint import register_fonts, style
```

and that's it.

The `style` function covers all plotting utilities. `register_fonts` is a convenience function to make Matplotlib aware of fonts installed on your computer. It is needed because Matplotlib is notoriously bad with font caches. My workflow is to try using all fonts directly (more on this below), and whenever this fails (you might see something like `findfont: Font family 'Roboto Condensed Light' not found.`), I register the font manually instead of refreshing Matplotlib's unreliable caches and praying.

The API is designed to make it easy to switch between paper and talk/meeting plots. Paper plots are rigid: the background is always white and font families, font sizes, and figure sizes are determined by the conference's formatting instructions. Slides are completely different: one gets complete freedom to choose backgrounds, used font families, and aspect ratios that affect figure sizes, too. Copy-pasting paper plots into such slides just doesn't look right. But one also doesn't want to spend entire afternoons converting paper plots to match the slide styles. This is where the package comes in handy: switching between the supported themes, different fonts, or figure sizes takes seconds. I highly recommend using `figmint` together with `slidemint` which supports the same themes for `beamer`, making them interact seamlessly.

```python
import matplotlib.pyplot as plt
from pathlib import Path
from figmint import register_fonts, style

# Register fonts if Matplotlib doesn't see them
SLIDE_FONT_FILES = (
    Path.home() / "Library/Fonts/RobotoCondensed-VariableFont_wght.ttf",
    Path.home() / "Library/Fonts/RobotoCondensed-Italic-VariableFont_wght.ttf",
)
register_fonts(*SLIDE_FONT_FILES)


# Define a simple plotting function
def plot(path: Path) -> None:
    figure, axis = plt.subplots()

    xs = list(range(81))
    ys = [x**2 for x in xs]

    axis.plot(xs, ys)
    axis.set_xlabel(r"$x$")
    axis.set_ylabel(r"$f(x)$")

    figure.savefig(path)
    plt.close(figure)


# Create paper plot
with plt.rc_context(style("normal", venue="icml", column="half")):
    plot(Path("figure_paper.pdf"))


# Create talk plot by only modifying the style
with plt.rc_context(
    style(
        theme="frappe",
        venue="icml",
        column="half",
        font="Roboto Condensed",
        font_weight="light",
        font_size=13.0,
        figure_size=(7.5, 4.25),
    )
):
    plot(Path("figure_talk.pdf"))
```

You can also apply a style globally:

```python
plt.rcParams.update(style("normal", venue="icml", column="half"))
```

## Themes

Supported themes are:

- `normal`
- `latte`
- `frappe`
- `macchiato`
- `mocha`

`normal` uses a white background, black text, black edges, a repaired Catppuccin Latte categorical cycle, and Matplotlib's built-in `plasma` colormap for scalar data. Paper figures also use framed legends and a low-alpha default grid. The normal categorical cycle keeps the Latte ordering and changes the fewest possible entries needed to meet the white-background contrast and CVD-separation checks used for the package.

### Normal Color Cycle

The `normal` color cycle is a constrained repair of the Catppuccin Latte cycle to adhere to academic plotting best practices. We chose the Catppuccin Latte cycle as the initialization because we love it wholeheartedly.

Let $p_i$ be the original Latte color at cycle index $i$ and $c_i$ be the repaired color at the same index. We ran a finite, quantized sRGB search problem on 8-bit colors. The objective was lexicographic: $$\operatorname{lexmin}_{c_1,\ldots,c_n}\left(\sum_i \mathbf{1}[c_i \ne p_i], \sum_i d_{\mathrm{OKLab}}(c_i,p_i)^2\right)$$

The constraints were:

- fixed ordering: color $c_i$ stays at Latte cycle position $i$;
- exact preservation when possible: $c_i=p_i$ unless moving it is needed for a constraint;
- white-background contrast: $C(c_i,\mathrm{white}) \ge 3.0$ for every repaired color;
- color-vision separation: $\Delta_m(c_i,c_j) \ge \tau$ for every distinct pair $i \ne j$ and every simulated mode $m$ in the protan, deutan, and tritan family.

The first objective counts how many Latte entries moved. The second objective keeps the moved colors close to their original Latte colors. This makes the intervention minimal in the useful sense: keep the Catppuccin identity and ordering, then move only the entries that must move, then move them as little as possible.

Gray-scale separation is deliberately excluded from the constraints. The target medium is digital color academic figures, and in 2026 that is the main reading path. A gray-scale constraint forces the palette to spend contrast budget on luminance ordering, which fights the color-vision constraints and makes the colors worse for the actual default use case. For black-and-white output, the right mechanism is redundant encoding: markers, line styles, hatches, direct labels, or separate figure variants.

The Catppuccin colors used by the themed styles are official palette values. Each themed style sets both the line/bar color cycle and a sequential Matplotlib colormap built from the theme background, main accent, and text colors. Dark themes set the axes, figure, and saved-output background to the theme base color, so exported plots can be imported into matching slide decks without a white rectangle.

## Venue Presets

Venue presets set the default figure size, font size, and font for paper figures. ICML uses `8 pt`; ICLR and NeurIPS use `9 pt`. All supported venue presets default to `Times New Roman`. `font`, `font_weight`, `font_size`, and `figure_size` are overrides; omit them to use the venue preset. To make a talk version, change the theme and override the font and size fields when needed. If Matplotlib cannot already see the target font, call `register_fonts(...)` once before rendering.

Choose one of:

- `venue="iclr"`
- `venue="neurips"`
- `venue="icml"`

ICML supports `column="half"` and `column="full"`. ICLR and NeurIPS use `column="full"`.

Minimal calls:

```python
style("normal", venue="icml", column="half")
style(
    "frappe",
    venue="icml",
    column="half",
    font="Roboto Condensed",
    font_weight="light",
    font_size=13.0,
    figure_size=(7.5, 4.25),
)
```

## Customization

`style(...)` accepts:

- `theme`
- `venue`
- `column`
- `width_fraction`
- `rows`
- `cols`
- `usetex`
- `font`
- `font_weight`
- `font_size`
- `figure_size`
- `line_width`
- `grid_alpha`
- `height_to_width_ratio`
