# figmint

`figmint` is my Matplotlib style collection. I use it to create plots for papers, talks, and meetings.

`figmint` deliberately has a small API, making it easy to grasp:

```python
from figmint import register_fonts, style
```

and that's it.

- `style(...)` returns an `rcParams` dictionary;
- `register_fonts(...)` registers local font files with Matplotlib before a style refers to those font families.

The `style` function covers all plotting utilities. `register_fonts` is a convenience function to make Matplotlib aware of fonts installed on your computer. It is needed because Matplotlib is notoriously bad with font caches. My workflow is to try using all fonts directly (more on this below), and whenever this fails (you might see something like `findfont: Font family 'Roboto Condensed Light' not found.`), I register the font manually instead of refreshing Matplotlib's unreliable caches and praying.

The API is designed to make it easy to switch between paper and talk/meeting plots. Paper plots are rigid: the background is always white and font families, font sizes, and figure sizes are determined by the conference's formatting instructions. Slides are completely different: one gets complete freedom to choose backgrounds, used font families, and aspect ratios that affect figure sizes, too. Copy-pasting paper plots into such slides just doesn't look right. But one also doesn't want to spend entire afternoons converting paper plots to match the slide styles. This is where the package comes in handy: switching between the supported themes, different fonts, or figure sizes takes seconds. I highly recommend using `figmint` together with `slidemint` which supports the same themes for `beamer`, making them interact seamlessly.

```python
import matplotlib.pyplot as plt
from pathlib import Path
from matplotlib.axes import Axes
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

`normal` uses a white background, black text, black edges, and the Latte color cycle. The Catppuccin colors used by the themed styles are official palette values. Each style sets both the line/bar color cycle and the default Matplotlib colormap. Dark themes set the axes, figure, and saved-output background to the theme base color, so exported plots can be imported into matching slide decks without a white rectangle.

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

## Gallery

Run the preview script to render PDFs for themes, layouts, and plot types:

```bash
uv run --with matplotlib preview.py theme_preview
```

The output is organized into:

- `themes/`: one convergence figure per theme, plus the talk override example
- `layouts/`: single-panel and multi-panel venue layouts
- `plot_types/`: line, bar, contour, and surface plots

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
