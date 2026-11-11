"""Saving a figure with the commit, the script, and the results in its metadata."""

import subprocess  # noqa: S404  # fixed git subcommands on a path this module chose
import sys
from os import PathLike
from pathlib import Path

from matplotlib.backends.backend_pgf import FigureCanvasPgf
from matplotlib.figure import Figure

from figmint._ticks import format_ticks

# TeX's special characters and how hyperref reads them back into a PDF string.
TEX_SPECIALS = {
    "\\": r"\textbackslash{}",
    "{": r"\{",
    "}": r"\}",
    "$": r"\$",
    "&": r"\&",
    "#": r"\#",
    "^": r"\textasciicircum{}",
    "_": r"\_",
    "%": r"\%",
    "~": r"\textasciitilde{}",
}


def savefig(
    figure: Figure,
    path: str | PathLike[str],
    *,
    results: str | PathLike[str] | None = None,
    repo: str | PathLike[str] | None = None,
) -> None:
    """Save a figure with its provenance in the file's metadata.

    The tick numbers of the figure are formatted by the look first. The
    repository that drew the figure, its commit, the script that ran, and the
    results it read go into the PDF information dictionary or the PNG text
    chunks, so that a figure found in a paper can be traced back to the code
    and the data that produced it. Outside a git repository the call fails
    with ``RuntimeError`` rather than write a figure with no provenance.

    Args:
        figure: The figure to save.
        path: Where to write it. The suffix selects the format, as in
            ``Figure.savefig``.
        results: The directory of the results the script read, recorded as
            given. Pass a path relative to the repository so the record stays
            valid on another machine.
        repo: A directory inside the repository to record. Defaults to the
            directory of the running script.
    """
    save(figure, path, provenance(results=results, repo=repo))


def save(figure: Figure, path: str | PathLike[str], metadata: dict[str, str]) -> None:
    """Format the tick numbers and save the figure with the metadata.

    The pgf backend typesets metadata, so its TeX special characters are
    escaped for that canvas.
    """
    format_ticks(figure)

    if isinstance(figure.canvas, FigureCanvasPgf):
        metadata = {key: tex_escape(value) for key, value in metadata.items()}

    figure.savefig(path, metadata=metadata)


def tex_escape(text: str) -> str:
    """Return the text with TeX's special characters escaped."""
    return "".join(TEX_SPECIALS.get(character, character) for character in text)


def provenance(
    *,
    results: str | PathLike[str] | None = None,
    repo: str | PathLike[str] | None = None,
) -> dict[str, str]:
    """Return the metadata ``savefig`` writes, for callers that save another way.

    Args:
        results: The directory of the results the script read, recorded as given.
        repo: A directory inside the repository to record. Defaults to the
            directory of the running script.

    Returns:
        A ``Creator`` entry naming figmint and a ``Subject`` entry of the form
        ``repo=<name> commit=<sha> script=<path> results=<path>``. The
        ``script`` field is omitted when the running script is not inside the
        repository, and ``results`` when none was given. Outside a git
        repository the call fails with ``RuntimeError``.
    """
    script = Path(sys.argv[0]).resolve()
    where = Path(repo).expanduser().resolve() if repo is not None else script.parent
    top = Path(_git(where, "rev-parse", "--show-toplevel"))
    commit = _git(where, "rev-parse", "HEAD")
    fields = [f"repo={top.name}", f"commit={commit}"]

    if script.is_relative_to(top):
        fields.append(f"script={script.relative_to(top).as_posix()}")

    if results is not None:
        fields.append(f"results={Path(results).as_posix()}")

    return {"Creator": "figmint", "Subject": " ".join(fields)}


def _git(where: Path, *arguments: str) -> str:
    # The arguments are fixed git subcommands and a path this module chose, never input
    # from outside the process.
    completed = subprocess.run(  # noqa: S603
        ["git", "-C", str(where), *arguments],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
    )

    if completed.returncode != 0:
        msg = f"git {' '.join(arguments)} failed in {where}: {completed.stderr.strip()}"
        raise RuntimeError(msg)

    return completed.stdout.strip()
