module = "figmint"

sourcefiledir = "tex/latex/figmint"
sourcefiles = { "*.sty" }
installfiles = { "*.sty" }
unpackfiles = { }
testfiledir = "testfiles"
checkengines = { "luatex" }

local tests = {
  "catppuccin-check",
  "tikzscale-check",
  "legend-optimizer-check",
}

local log_needles = {
  "Missing character",
  "Fatal error",
  "Undefined control sequence",
  "LaTeX Error",
  "Emergency stop",
  "LaTeX Warning:",
  "LaTeX Font Warning:",
  "Overfull \\hbox",
  "Overfull \\vbox",
  "Underfull \\hbox",
  "Underfull \\vbox",
}

local function quote(value)
  return "'" .. string.gsub(value, "'", "'\\''") .. "'"
end

local function run(label, command)
  print(label)
  local result = os.execute(command)
  if result == true or result == 0 then
    return 0
  end
  return 1
end

local function file_contains(path, needle)
  local handle = io.open(path, "r")
  if not handle then
    return false
  end
  local content = handle:read("*a")
  handle:close()
  return string.find(content, needle, 1, true) ~= nil
end

local function line_has_log_problem(line)
  if string.sub(line, 1, 1) == "!" then
    return true
  end
  if string.match(line, "^Package .+ Error") then
    return true
  end
  if string.match(line, "^Package .+ Warning:") then
    return true
  end
  if string.match(line, "^Class .+ Error") then
    return true
  end
  if string.match(line, "^Class .+ Warning:") then
    return true
  end
  for _, needle in ipairs(log_needles) do
    if string.find(line, needle, 1, true) then
      return true
    end
  end
  return false
end

local function scan_log(path)
  for line in io.lines(path) do
    if line_has_log_problem(line) then
      print(path .. ": " .. line)
      return 1
    end
  end
  return 0
end

local function compile_test(name)
  local texinputs = table.concat({
    "./tex/latex/figmint",
    "",
  }, ":")
  local command = "env TEXINPUTS=" .. quote(texinputs)
    .. " TEXMFVAR=" .. quote("build/texmf-var")
    .. " TEXMFCACHE=" .. quote("build/texmf-var")
    .. " lualatex -halt-on-error -interaction=nonstopmode"
    .. " -output-directory=build"
    .. " " .. quote("testfiles/" .. name .. ".tex")

  if run("lualatex " .. name, command) ~= 0 then
    return 1
  end
  return run("lualatex " .. name, command)
end

local function compile_error_test()
  local texinputs = table.concat({
    "./tex/latex/figmint",
    "",
  }, ":")
  local command = "env TEXINPUTS=" .. quote(texinputs)
    .. " TEXMFVAR=" .. quote("build/texmf-var")
    .. " TEXMFCACHE=" .. quote("build/texmf-var")
    .. " lualatex -halt-on-error -interaction=nonstopmode"
    .. " -output-directory=build"
    .. " " .. quote("testfiles/validation-error-check.tex")

  if run("lualatex validation-error-check expected error", command) == 0 then
    print("validation-error-check: expected TeX error did not occur")
    return 1
  end

  local needle = "Package figmint Error: rows must be a positive integer"
  if not file_contains("build/validation-error-check.log", needle) then
    print("build/validation-error-check.log: missing expected validation error")
    return 1
  end
  return 0
end

local function output_checks()
  local checks = {
    { "build/catppuccin-check.log", "FIGMINT_COLOR name=FigmintWhite;hex=FFFFFF;expected=FFFFFF" },
    { "build/catppuccin-check.log", "FIGMINT_COLOR name=FigmintFrappeEdge;hex=737994;expected=737994" },
    { "build/catppuccin-check.log", "FIGMINT_COLOR name=FigmintMochaCrust;hex=11111B;expected=11111B" },
    { "build/legend-optimizer-check.log", "FIGMINT_LEGEND name=auto-matrix;mode=best;" },
    { "build/legend-optimizer-check.log", "FIGMINT_LEGEND name=ybar;mode=best;" },
  }

  for _, check in ipairs(checks) do
    if not file_contains(check[1], check[2]) then
      print(check[1] .. ": missing " .. check[2])
      return 1
    end
  end
  return 0
end

local function figmint_check()
  if run("create build directory", "mkdir -p build/texmf-var") ~= 0 then
    return 1
  end

  for _, test in ipairs(tests) do
    if compile_test(test) ~= 0 then
      return 1
    end
  end

  if compile_error_test() ~= 0 then
    return 1
  end

  if output_checks() ~= 0 then
    return 1
  end

  for _, test in ipairs(tests) do
    if scan_log("build/" .. test .. ".log") ~= 0 then
      return 1
    end
  end

  return 0
end

target_list.check.func = function()
  return figmint_check()
end
