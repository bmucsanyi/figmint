-- Test harness of the mint suite, shared by figmint, macromint, papermint, and
-- slidemint. The build.lua of figmint loads it with dofile. The other three
-- load ../figmint/harness.lua inside their check target, so that their
-- l3build install works without a checkout of figmint.
--
-- A test is testfiles/<name>.tex. Compiling it with an engine writes
-- build/<name>-<engine>.pdf and build/<name>-<engine>.log. The environment of
-- a test is a table of variables for the engine, such as TEXINPUTS. Functions
-- that can fail return 0 on success and 1 on failure, as the check target of
-- l3build does.

local harness = {}

-- Lines of a log that mark a problem, besides the errors and warnings of
-- packages and classes.
local log_needles = {
  "Missing character",
  "Fatal error",
  "Undefined control sequence",
  "LaTeX Error",
  "Could not resolve font",
  "Emergency stop",
  "LaTeX Warning:",
  "LaTeX Font Warning:",
  "Overfull \\hbox",
  "Overfull \\vbox",
  "Underfull \\hbox",
  "Underfull \\vbox",
}

function harness.quote(value)
  return "'" .. string.gsub(value, "'", "'\\''") .. "'"
end

-- Runs a shell command under a label and returns 0 when it succeeded.
function harness.run(label, command)
  print(label)
  local result = os.execute(command)
  if result == true or result == 0 then
    return 0
  end
  return 1
end

function harness.file_contains(path, needle)
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

-- Prints the first line of a log that marks a problem and returns 1, or
-- returns 0 when the log holds none.
function harness.scan_log(path)
  for line in io.lines(path) do
    if line_has_log_problem(line) then
      print(path .. ": " .. line)
      return 1
    end
  end
  return 0
end

-- The file an engine writes for a test: build/<name>-<engine>.<extension>.
function harness.output(name, engine, extension)
  return "build/" .. name .. "-" .. engine .. "." .. extension
end

-- The TEXINPUTS value that searches the given directories before the
-- installed tree.
function harness.texinputs(directories)
  return table.concat(directories, ":") .. ":"
end

-- The TeX directory of a sibling checkout, for texinputs. Stops when the
-- checkout is missing, so that a test never silently uses an installed copy.
function harness.require_sibling(name)
  local directory = "../" .. name .. "/tex/latex/" .. name
  if lfs.attributes(directory, "mode") ~= "directory" then
    print(directory .. " is missing: the tests need a checkout of " .. name
      .. " next to this repository")
    os.exit(1)
  end
  return directory
end

-- The env prefix of a command: the variables of the test environment, with
-- the font caches of the engines kept inside build/.
local function env_prefix(environment)
  local assignments = {
    "TEXMFVAR=" .. harness.quote("build/texmf-var"),
    "TEXMFCACHE=" .. harness.quote("build/texmf-var"),
  }
  for name, value in pairs(environment) do
    table.insert(assignments, name .. "=" .. harness.quote(value))
  end
  return "env " .. table.concat(assignments, " ")
end

-- The command that compiles testfiles/<name>.tex with an engine into build/.
-- Long log lines stay unwrapped, so that checks can match whole reports.
function harness.tex_command(environment, name, engine)
  return env_prefix(environment)
    .. " max_print_line=10000"
    .. " " .. engine
    .. " -halt-on-error -interaction=nonstopmode"
    .. " -jobname=" .. harness.quote(name .. "-" .. engine)
    .. " -output-directory=build"
    .. " " .. harness.quote("testfiles/" .. name .. ".tex")
end

local function prepare_build_directory()
  lfs.mkdir("build")
  lfs.mkdir("build/texmf-var")
end

-- Compiles a test twice, so that references and labels settle. When the first
-- compile writes a biblatex control file, biber runs before the second
-- compile and a third compile follows.
function harness.compile_test(environment, name, engine)
  prepare_build_directory()
  local command = harness.tex_command(environment, name, engine)
  local label = engine .. " " .. name
  if harness.run(label, command) ~= 0 then
    return 1
  end
  if lfs.attributes(harness.output(name, engine, "bcf"), "mode") == "file" then
    local biber = env_prefix(environment)
      .. " biber --input-directory build --output-directory build "
      .. harness.quote(name .. "-" .. engine)
    if harness.run("biber " .. name, biber) ~= 0 then
      return 1
    end
    if harness.run(label, command) ~= 0 then
      return 1
    end
  end
  return harness.run(label, command)
end

-- Compiles a test once, expects the engine to stop with an error, and checks
-- that the log holds the expected message.
function harness.compile_error_test(environment, name, engine, needle)
  prepare_build_directory()
  local command = harness.tex_command(environment, name, engine)
  if harness.run(engine .. " " .. name .. " expected error", command) == 0 then
    print(name .. ": expected TeX error did not occur")
    return 1
  end
  local log = harness.output(name, engine, "log")
  if not harness.file_contains(log, needle) then
    print(log .. ": missing " .. needle)
    return 1
  end
  return 0
end

return harness
