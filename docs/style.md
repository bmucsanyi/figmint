# The look of a figure

figmint draws every figure by these rules, through the settings of `style` and `Document`, the tick formatter, and the plot functions. `docs/legend.md` states the legend rule.

- Grid lines along the value axis only: horizontal lines, vertical ones for horizontal bars, and none for scatter plots and heat maps.
- Bars filled with 30% of their color over the background and outlined in their color. A single bar is 0.4125 of the spacing wide. The bars of a group share 0.8 of the spacing, each at most 0.22 of it.
- Boxes 0.55 of the spacing wide with caps 0.44 wide, filled with 12% of their color over the background and outlined in it, the median as wide as a plot line, the whiskers as an axis line, and no fliers.
- A colorbar 4 bp wide, 4 bp from the axes and as tall, with no frame.
- Bands with opacity 0.18 and no edge.
- Numbers in math mode, as pgfplots and siunitx set numbers: the digits, the decimal point, and the minus sign come from the document's math font. No trailing zeros.
- Automatic limits as the range of the data enlarged by 5% on each side.
- The canvas exactly the requested size, with the content 3 bp inside it.
- Axis lines 0.5 bp wide, plot lines 1 bp, markers 3 bp, major ticks 3 bp long and outside the axes, only the left and bottom spines, and a legend without a frame line.
- The colors of the theme: `normal` on white, and the Catppuccin palettes `latte`, `frappe`, `macchiato`, and `mocha` on their base color, with `plasma` for scalar fields.
