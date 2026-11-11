module = "figmint"

sourcefiledir = "tex/latex/figmint"
sourcefiles = { "*.sty" }
installfiles = { "*.sty" }
unpackfiles = { }

local harness = dofile("harness.lua")

local environment = {
  TEXINPUTS = harness.texinputs({
    "./tex/latex/figmint",
    harness.require_sibling("macromint"),
    harness.require_sibling("slidemint"),
  }),
  -- minted, which slidemint loads, runs latexminted from this environment.
  PATH = "../slidemint/.venv/bin:" .. os.getenv("PATH"),
}

local engines = {
  "lualatex",
  "xelatex",
  "pdflatex",
}

-- The documents that write a .figmint file and include figures, with the
-- engine that compiles them and the directory their figures are read from.
local documents = {
  { name = "article-check", engine = "pdflatex", figures = "build/article-figures" },
  { name = "subcaption-check", engine = "pdflatex", figures = "build/subcaption-figures" },
  { name = "deck-check", engine = "lualatex", figures = "build/deck-figures" },
}

local color_checks = {
  "FIGMINT_COLOR name=FigmintWhite;hex=FFFFFF;expected=FFFFFF",
  "FIGMINT_COLOR name=FigmintFrappeEdge;hex=737994;expected=737994",
  "FIGMINT_COLOR name=FigmintMochaCrust;hex=11111B;expected=11111B",
}

local function read_file(path)
  local handle = io.open(path, "r")
  if not handle then
    print(path .. ": missing")
    return nil
  end
  local content = handle:read("*a")
  handle:close()
  return content
end

-- Parses a .figmint file into its header lines and its figures, each with the
-- fields of its line and the number of lines that named it.
local function parse_figmint(path)
  local content = read_file(path)
  if not content then
    return nil
  end
  local file = { header = {}, figures = {} }
  for line in string.gmatch(content, "[^\n]+") do
    local name, width, height, rows, cols, theme, size, script, scriptscript, family, series, shape =
      string.match(line, "^figure=([^;]+);width=([%d.]+);height=([%d.]+);rows=(%d+);cols=(%d+);"
        .. "theme=(%w+);size=([%d.]+);script=([%d.]+);scriptscript=([%d.]+);"
        .. "family=([%w-]+);series=(%w+);shape=(%w+);fonts=")
    if name then
      local figure = file.figures[name]
      if figure then
        figure.count = figure.count + 1
      else
        file.figures[name] = {
          width = tonumber(width), height = tonumber(height),
          rows = tonumber(rows), cols = tonumber(cols), theme = theme,
          size = tonumber(size), script = tonumber(script), scriptscript = tonumber(scriptscript),
          family = family, series = series, shape = shape, count = 1,
        }
      end
    else
      table.insert(file.header, line)
    end
  end
  return file
end

-- The \linewidth values that a test document reports through \typeout.
local function linewidths(log_path)
  local content = read_file(log_path)
  local widths = {}
  for name, width in string.gmatch(content, "FIGMINT_TEST name=(%w+);linewidth=([%d.]+)pt") do
    widths[name] = tonumber(width)
  end
  return widths
end

local function count_in(content, needle)
  local count = 0
  local position = 1
  while true do
    local found = string.find(content, needle, position, true)
    if not found then
      return count
    end
    count = count + 1
    position = found + #needle
  end
end

local function pages(pdf)
  local handle = io.popen("pdfinfo " .. harness.quote(pdf))
  local output = handle:read("*a")
  handle:close()
  return tonumber(string.match(output, "Pages:%s+(%d+)"))
end

local function near(label, actual, expected, tolerance)
  if actual == nil or math.abs(actual - expected) > tolerance then
    print(label .. ": got " .. tostring(actual) .. ", expected " .. tostring(expected))
    return false
  end
  return true
end

local function equal(label, actual, expected)
  if actual ~= expected then
    print(label .. ": got " .. tostring(actual) .. ", expected " .. tostring(expected))
    return false
  end
  return true
end

-- A PDF of exactly the given size in pt, standing in for a drawn figure.
local function make_fixture(directory, name, width, height)
  lfs.mkdir(directory)
  local source = "\\documentclass{article}\n"
    .. "\\usepackage[paperwidth=" .. width .. "pt,paperheight=" .. height .. "pt,margin=0pt]{geometry}\n"
    .. "\\pagestyle{empty}\n\\begin{document}\n\\null\n\\end{document}\n"
  local path = directory .. "/" .. name .. ".tex"
  local handle = io.open(path, "w")
  handle:write(source)
  handle:close()
  return harness.run("fixture " .. name,
    "pdflatex -halt-on-error -interaction=nonstopmode -output-directory=" .. harness.quote(directory)
      .. " " .. harness.quote(path) .. " > /dev/null")
end

local function make_fixtures(document, file)
  for name, figure in pairs(file.figures) do
    if make_fixture(document.figures, name, figure.width, figure.height) ~= 0 then
      return 1
    end
  end
  return 0
end

-- Compiles a document without figures, which must warn for each, then with
-- fixtures of the sizes it asked for, which must compile clean with the same
-- number of pages.
local function compile_document(document)
  if harness.run("clear fixtures", "rm -rf " .. harness.quote(document.figures)) ~= 0 then
    return nil
  end
  if harness.compile_test(environment, document.name, document.engine) ~= 0 then
    return nil
  end
  local log_path = harness.output(document.name, document.engine, "log")
  local pdf = harness.output(document.name, document.engine, "pdf")
  local file = parse_figmint(harness.output(document.name, document.engine, "figmint"))
  if not file then
    return nil
  end
  local without = pages(pdf)
  for name in pairs(file.figures) do
    if not harness.file_contains(log_path, "Package figmint Warning: Figure " .. name .. " is not drawn yet") then
      print(log_path .. ": missing the warning that " .. name .. " is not drawn yet")
      return nil
    end
  end
  if make_fixtures(document, file) ~= 0 then
    return nil
  end
  if harness.compile_test(environment, document.name, document.engine) ~= 0 then
    return nil
  end
  if harness.file_contains(log_path, "Package figmint Warning") then
    print(log_path .. ": a figmint warning with fixtures of the right size")
    return nil
  end
  if not equal(document.name .. " pages with and without figures", pages(pdf), without) then
    return nil
  end
  return file
end

local function check_header(document, file)
  local content = table.concat(file.header, "\n")
  local expected = {
    "figmint=0.1.0",
    "engine=" .. document.engine,
    "directory=" .. document.figures .. "/",
  }
  for _, line in ipairs(expected) do
    if count_in(content, line) ~= 1 then
      print(document.name .. ": expected one line " .. line)
      return false
    end
  end
  return true
end

local function check_preamble_lines(document, file, lines)
  local content = table.concat(file.header, "\n")
  for _, line in ipairs(lines) do
    if count_in(content, "preamble=" .. line) ~= 1 then
      print(document.name .. ": expected one preamble line " .. line)
      return false
    end
  end
  return true
end

local function check_caption(document, figure, name, size, script, scriptscript, family)
  local label = document.name .. " " .. name
  return near(label .. " size", figure.size, size, 0.001)
    and near(label .. " script", figure.script, script, 0.001)
    and near(label .. " scriptscript", figure.scriptscript, scriptscript, 0.001)
    and equal(label .. " family", figure.family, family)
    and equal(label .. " series", figure.series, "m")
    and equal(label .. " shape", figure.shape, "n")
end

local function check_article(document, file)
  local widths = linewidths(harness.output(document.name, document.engine, "log"))
  local first, second = file.figures.first, file.figures.second
  if not (first and second) then
    print("article-check: missing a figure line")
    return false
  end
  return check_header(document, file)
    and check_preamble_lines(document, file, {
      "\\usepackage[OT1]{fontenc}",
      "\\renewcommand{\\rmdefault}{ptm}",
      "\\usepackage {amsmath}",
    })
    and near("article first width", first.width, widths.article, 0.001)
    and near("article first height", first.height, 0.6180339887498948 * widths.article, 0.001)
    and near("article second width", second.width, 0.5 * widths.article, 0.001)
    and near("article second height", second.height, 0.5 * 0.5 * widths.article, 0.001)
    and equal("article second count", second.count, 1)
    and check_caption(document, first, "first", 10, 7, 5, "serif")
    and check_caption(document, second, "second", 10, 7, 5, "serif")
end

local function check_subcaption(document, file)
  local widths = linewidths(harness.output(document.name, document.engine, "log"))
  local sub, main = file.figures.sub, file.figures.main
  if not (sub and main) then
    print("subcaption-check: missing a figure line")
    return false
  end
  return check_header(document, file)
    and near("subfigure width", sub.width, widths.subfigure, 0.001)
    and near("main width", main.width, widths.subcaption, 0.001)
    and check_caption(document, sub, "sub", 8, 6, 5, "serif")
    and check_caption(document, main, "main", 9, 6, 5, "serif")
end

local function check_deck(document, file)
  local widths = linewidths(harness.output(document.name, document.engine, "log"))
  local first, second = file.figures.first, file.figures.second
  if not (first and second) then
    print("deck-check: missing a figure line")
    return false
  end
  return check_header(document, file)
    and check_preamble_lines(document, file, {
      "\\usepackage {slidemintfonts}",
      "\\usepackage {macromint}",
    })
    and near("deck first width", first.width, widths.column, 0.001)
    and near("deck first height", first.height, 0.48 * widths.column, 0.001)
    and near("deck second height", second.height, 0.5 * second.width, 0.001)
    -- The frame has two slides; the figure without an overlay is written on both.
    and equal("deck first count", first.count, 2)
    and equal("deck second count", second.count, 1)
    and check_caption(document, first, "first", 9, 6, 5, "sans-serif")
    and check_caption(document, second, "second", 9, 6, 5, "sans-serif")
end

local checks = {
  ["article-check"] = check_article,
  ["subcaption-check"] = check_subcaption,
  ["deck-check"] = check_deck,
}

-- A fixture of the wrong size gives a warning that prints both sizes, and
-- the document still compiles.
local function wrong_size_check()
  local document = documents[1]
  local file = parse_figmint(harness.output(document.name, document.engine, "figmint"))
  local first = file.figures.first
  if make_fixture(document.figures, "first", first.width + 10, first.height) ~= 0 then
    return 1
  end
  if harness.compile_test(environment, document.name, document.engine) ~= 0 then
    return 1
  end
  local log = read_file(harness.output(document.name, document.engine, "log"))
  local pattern = "Package figmint Warning: Figure first is [%d.]+pt by [%d.]+pt, and the document asks for "
    .. string.gsub(string.format("%.1f", first.width), "%.", "%%.") .. "pt by"
  if not string.find(log, pattern) then
    print(document.name .. ": missing the warning with both sizes")
    return 1
  end
  return 0
end

local function check()
  for _, engine in ipairs(engines) do
    if harness.compile_test(environment, "catppuccin-check", engine) ~= 0 then
      return 1
    end
    local log = harness.output("catppuccin-check", engine, "log")
    for _, needle in ipairs(color_checks) do
      if not harness.file_contains(log, needle) then
        print(log .. ": missing " .. needle)
        return 1
      end
    end
    if harness.scan_log(log) ~= 0 then
      return 1
    end
  end

  if harness.compile_error_test(environment, "validation-error-check", "pdflatex",
    "Package figmint Error: rows must be a positive integer") ~= 0 then
    return 1
  end

  for _, document in ipairs(documents) do
    local file = compile_document(document)
    if not file then
      return 1
    end
    if not checks[document.name](document, file) then
      return 1
    end
    if harness.scan_log(harness.output(document.name, document.engine, "log")) ~= 0 then
      return 1
    end
  end

  return wrong_size_check()
end

target_list.check.func = check
