"""Figure export with the code commit and the results written into the file."""

import subprocess  # noqa: S404  # fixed git subcommands on a path this module chose
import sys
from os import PathLike
from pathlib import Path

from matplotlib.figure import Figure


def savefig(
    figure: Figure,
    path: str | PathLike[str],
    *,
    results: str | PathLike[str] | None = None,
    repo: str | PathLike[str] | None = None,
) -> None:
    """Save a figure with its provenance in the file's metadata.

    The commit of the repository that drew the figure, whether that repository had
    uncommitted changes, the script that ran, and the results it read go into the PDF
    information dictionary or the PNG text chunks. A figure found in a paper or a deck
    can then be traced back to the code and the data that produced it. Outside a git
    repository the call fails with ``RuntimeError`` rather than write a figure with no
    provenance.

    Args:
        figure: The figure to save.
        path: Where to write it. The suffix selects the format, as in
            ``Figure.savefig``.
        results: The results the script read, recorded as given. Pass a path relative
            to the repository so the record stays valid on another machine.
        repo: A directory inside the repository to record. Defaults to the directory
            of the running script.
    """
    figure.savefig(path, metadata=provenance(results=results, repo=repo))


def provenance(
    *,
    results: str | PathLike[str] | None = None,
    repo: str | PathLike[str] | None = None,
) -> dict[str, str]:
    """Return the metadata ``savefig`` writes, for callers that save another way.

    Args:
        results: The results the script read, recorded as given.
        repo: A directory inside the repository to record. Defaults to the directory
            of the running script.

    Returns:
        A ``Creator`` entry naming figmint and a ``Subject`` entry of the form
        ``repo=<name> commit=<sha> dirty=<yes|no> script=<path> results=<path>``.
        The ``script`` field is omitted when the running script is not inside the
        repository, and ``results`` when none was given. Outside a git repository the
        call fails with ``RuntimeError``.
    """
    script = Path(sys.argv[0]).resolve()
    where = Path(repo).expanduser().resolve() if repo is not None else script.parent
    top = Path(_git(where, "rev-parse", "--show-toplevel"))
    commit = _git(where, "rev-parse", "HEAD")
    changes = _git(where, "status", "--porcelain", "--untracked-files=no")
    dirty = "yes" if changes else "no"
    fields = [f"repo={top.name}", f"commit={commit}", f"dirty={dirty}"]

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
