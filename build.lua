module = "figmint"

sourcefiledir = "tex/latex/figmint"
sourcefiles = { "*.sty" }
installfiles = { "*.sty" }
unpackfiles = { }

local harness = dofile("harness.lua")

local environment = {
  TEXINPUTS = harness.texinputs({ "./tex/latex/figmint" }),
}

-- Compiled with lualatex.
local tests = {
  "catppuccin-check",
  "caption-font-check",
  "beamer-caption-font-check",
  "semantic-grid-check",
  "tikzscale-check",
  "legend-optimizer-check",
  "surface-shading-check",
}

-- Compiled with every engine.
local engine_neutral_tests = {
  "engine-neutral-check",
}

local engines = {
  "lualatex",
  "xelatex",
  "pdflatex",
}

-- Expected legend placements of the fixtures shared with the matplotlib tests.
local function legend_cases()
  local cases = {}
  local header = true
  for line in io.lines("tests/fixtures/legend/cases.tsv") do
    if header then
      header = false
    else
      local name, _, _, location, anchor, columns =
        string.match(line, "^([^\t]+)\t([^\t]+)\t([^\t]+)\t([^\t]+)\t([^\t]+)\t([^\t]+)$")
      local mode = "fixed"
      if location == "best" then
        mode = "best"
      end
      table.insert(cases, {
        harness.output("legend-optimizer-check", "lualatex", "log"),
        "FIGMINT_LEGEND name=" .. name .. ";mode=" .. mode
          .. ";anchor=" .. anchor .. ";columns=" .. columns .. ";",
      })
    end
  end
  return cases
end

local function output_checks()
  local catppuccin = harness.output("catppuccin-check", "lualatex", "log")
  local caption = harness.output("caption-font-check", "lualatex", "log")
  local beamer_caption = harness.output("beamer-caption-font-check", "lualatex", "log")
  local grid = harness.output("semantic-grid-check", "lualatex", "log")
  local legend = harness.output("legend-optimizer-check", "lualatex", "log")
  local checks = {
    { catppuccin, "FIGMINT_COLOR name=FigmintWhite;hex=FFFFFF;expected=FFFFFF" },
    { catppuccin, "FIGMINT_COLOR name=FigmintFrappeEdge;hex=737994;expected=737994" },
    { catppuccin, "FIGMINT_COLOR name=FigmintMochaCrust;hex=11111B;expected=11111B" },
    { caption, "FIGMINT_FONT name=caption;size=9" },
    { caption, "FIGMINT_FONT name=primary;size=9" },
    { caption, "FIGMINT_FONT name=secondary;size=9" },
    { caption, "FIGMINT_FONT name=axis-label;size=9" },
    { caption, "FIGMINT_FONT name=tick;size=9" },
    { caption, "FIGMINT_FONT name=legend;size=9" },
    { caption, "FIGMINT_FONT name=node;size=9" },
    { caption, "FIGMINT_FONT name=colorbar;size=9" },
    { beamer_caption, "FIGMINT_FONT name=caption;size=10" },
    { beamer_caption, "FIGMINT_FONT name=primary;size=10" },
    { beamer_caption, "FIGMINT_FONT name=secondary;size=10" },
    { beamer_caption, "FIGMINT_FONT name=axis-label;size=10" },
    { beamer_caption, "FIGMINT_FONT name=tick;size=10" },
    { beamer_caption, "FIGMINT_FONT name=legend;size=10" },
    { beamer_caption, "FIGMINT_FONT name=node;size=10" },
    { beamer_caption, "FIGMINT_FONT name=colorbar;size=10" },
    { grid, "FIGMINT_GRID name=base;x=false;y=false" },
    { grid, "FIGMINT_GRID name=line;x=false;y=true" },
    { grid, "FIGMINT_GRID name=bar;x=false;y=true" },
    { grid, "FIGMINT_GRID name=horizontal-bar;x=true;y=false" },
    { grid, "FIGMINT_GRID name=mixed-line-horizontal-bar;x=true;y=true" },
    { grid, "FIGMINT_GRID name=mixed-horizontal-bar-line;x=true;y=true" },
    { grid, "FIGMINT_GRID name=scatter;x=false;y=false" },
    { grid, "FIGMINT_GRID name=heatmap;x=false;y=false" },
    { grid, "FIGMINT_COLORMAP name=frappe-heatmap;value=figmint plasma" },
    { legend, "FIGMINT_HOOK name=no-legend;finished-point=[]" },
  }

  for _, check in ipairs(legend_cases()) do
    table.insert(checks, check)
  end

  for _, check in ipairs(checks) do
    if not harness.file_contains(check[1], check[2]) then
      print(check[1] .. ": missing " .. check[2])
      return 1
    end
  end
  return 0
end

-- Reads a binary PPM image as written by pdftoppm.
local function read_ppm(path)
  local handle = io.open(path, "rb")
  if not handle then
    return nil
  end
  local data = handle:read("*a")
  handle:close()
  local width, height, offset = string.match(data, "^P6%s+(%d+)%s+(%d+)%s+%d+%s()")
  return { width = tonumber(width), height = tonumber(height), data = data, offset = offset }
end

local function pixel(image, x, y)
  local index = image.offset + 3 * (y * image.width + x)
  return { string.byte(image.data, index, index + 2) }
end

-- The two panels of surface-shading-check are constant shaded surfaces at
-- plasma(0.2) and plasma(0.8), as matplotlib computes them.
local function shading_checks()
  local pdf = harness.output("surface-shading-check", "lualatex", "pdf")
  if harness.run("render surface-shading-check",
    "pdftoppm -r 72 " .. harness.quote(pdf) .. " build/surface-shading-check") ~= 0 then
    return 1
  end

  local image = read_ppm("build/surface-shading-check-1.ppm")
  if not image then
    print("build/surface-shading-check-1.ppm: missing")
    return 1
  end

  local panels = {
    { image.width // 4, { 106, 0, 168 } },
    { 3 * image.width // 4, { 252, 166, 54 } },
  }
  for _, panel in ipairs(panels) do
    local color = pixel(image, panel[1], image.height // 2)
    for channel = 1, 3 do
      if math.abs(color[channel] - panel[2][channel]) > 3 then
        print("surface-shading-check: panel at x=" .. panel[1] .. " has color "
          .. table.concat(color, ",") .. ", expected " .. table.concat(panel[2], ","))
        return 1
      end
    end
  end
  return 0
end

local function check()
  for _, test in ipairs(tests) do
    if harness.compile_test(environment, test, "lualatex") ~= 0 then
      return 1
    end
  end

  for _, engine in ipairs(engines) do
    for _, test in ipairs(engine_neutral_tests) do
      if harness.compile_test(environment, test, engine) ~= 0 then
        return 1
      end
    end
  end

  if harness.compile_error_test(environment, "validation-error-check", "lualatex",
    "Package figmint Error: rows must be a positive integer") ~= 0 then
    return 1
  end

  if output_checks() ~= 0 then
    return 1
  end

  if shading_checks() ~= 0 then
    return 1
  end

  for _, test in ipairs(tests) do
    if harness.scan_log(harness.output(test, "lualatex", "log")) ~= 0 then
      return 1
    end
  end

  for _, engine in ipairs(engines) do
    for _, test in ipairs(engine_neutral_tests) do
      if harness.scan_log(harness.output(test, engine, "log")) ~= 0 then
        return 1
      end
    end
  end

  return 0
end

target_list.check.func = check
