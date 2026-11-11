"""Saving a figure with the commit, the script, and the results in its metadata."""

import subprocess  # noqa: S404  # fixed git subcommands on a path this module chose
import sys
from io import BytesIO
from os import PathLike
from pathlib import Path

from matplotlib.figure import Figure
from pypdf import PdfWriter

from figmint._ticks import format_ticks


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

    The metadata of a PDF is written into its information dictionary after
    the save, so that it arrives as given: the pgf backend would typeset it as
    LaTeX, which drops an underscore and refuses a backslash or a bracket.
    """
    format_ticks(figure)

    if Path(path).suffix.lower() == ".pdf":
        figure.savefig(path)
        write_pdf_metadata(path, metadata)
    else:
        figure.savefig(path, metadata=metadata)


def write_pdf_metadata(path: str | PathLike[str], metadata: dict[str, str]) -> None:
    """Set entries of the information dictionary of a PDF.

    The entries go into an incremental update appended to the file, so the
    bytes the engine wrote, its header included, stay as they are.
    """
    writer = PdfWriter(fileobj=str(path), incremental=True)
    writer.add_metadata({f"/{key}": value for key, value in metadata.items()})
    update = BytesIO()
    writer.write(update)
    Path(path).write_bytes(update.getvalue())


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
