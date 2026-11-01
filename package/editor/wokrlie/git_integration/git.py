"""Git command execution and output parsing for the Git panel.

Every call to the ``git`` executable lives in this module. It never touches
the Engine API, so the panel can run it on a worker thread without any
Engine state involved.

The status format is ``git status --porcelain=v2 -z --branch``:

* ``-z`` keeps paths verbatim, so a file called ``名字 file.txt`` is not
  escaped into ``"\\345\\220..."`` the way the older v1 format does.
* ``--branch`` adds the branch header lines, so the current branch, its
  upstream, and the ahead/behind counts arrive with the file list instead
  of costing another process launch.
"""

from __future__ import annotations

import subprocess
import threading
from dataclasses import dataclass, field
from typing import Any, Callable


#: Timeout for the read-only commands.
GIT_TIMEOUT = 15.0
#: Timeout for the commands that rewrite the working tree.
MUTATION_TIMEOUT = 120.0
#: Timeout for the branch name validation call.
VALIDATION_TIMEOUT = 10.0

#: ``for-each-ref`` format: refname, short name, upstream, current marker.
_BRANCH_FORMAT = "%(refname)%09%(refname:short)%09%(upstream:short)%09%(HEAD)"


@dataclass(frozen=True)
class CommandResult:
    """The outcome of one git command."""

    returncode: int
    stdout: str = ""
    stderr: str = ""
    #: The command line that was run. The Console entry quotes it, so a
    #: failure can be reproduced by hand.
    command: str = ""

    @property
    def ok(self) -> bool:
        return self.returncode == 0

    @property
    def summary(self) -> str:
        """One readable line describing a failure."""
        for text in (self.stderr, self.stdout):
            for line in text.splitlines():
                message = line.strip()
                if message:
                    return message
        return f"exit code {self.returncode}"


@dataclass
class StatusSnapshot:
    """The repository state as of one status call."""

    staged: dict[str, str] = field(default_factory=dict)
    unstaged: dict[str, str] = field(default_factory=dict)
    untracked: list[str] = field(default_factory=list)
    branch: str = ""
    detached: bool = False
    upstream: str = ""
    ahead: int = 0
    behind: int = 0
    #: The commit HEAD points at, used to name a detached HEAD.
    oid: str = ""

    @property
    def change_count(self) -> int:
        return len(self.unstaged) + len(self.untracked)


@dataclass(frozen=True)
class BranchInfo:
    """One branch, local or remote."""

    name: str
    remote: bool = False
    current: bool = False
    upstream: str = ""


class GitRunner:
    """Runs git commands against one repository."""

    def __init__(self, cwd: str) -> None:
        self.cwd = cwd

    def run(self, *args: str, timeout: float = GIT_TIMEOUT) -> CommandResult:
        """Run one git command and capture its output.

        The output is decoded as UTF-8 on purpose. Branch names and file
        paths are UTF-8 regardless of the system locale, and decoding them
        with the locale encoding mangles them on a Windows that is not
        running in UTF-8.
        """
        command = "git " + " ".join(args)
        try:
            completed = subprocess.run(
                ["git", *args],
                cwd=self.cwd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )
        except FileNotFoundError:
            return CommandResult(127, "", "Git is not installed.", command)
        except subprocess.TimeoutExpired:
            return CommandResult(
                124, "", f"`{command}` timed out after {timeout:g}s.", command
            )
        except OSError as exc:
            return CommandResult(1, "", str(exc), command)
        return CommandResult(
            completed.returncode, completed.stdout, completed.stderr, command
        )


class GitCommand:
    """One unit of work running on a worker thread.

    The thread only runs the callable and stores its result, so it never
    touches Engine state and the render thread keeps drawing while a slow
    ``git checkout`` works through a large repository.
    """

    def __init__(self, task: Callable[[], Any], name: str = "git-task") -> None:
        self._task = task
        self._name = name
        self._result: Any = None
        self._thread: threading.Thread | None = None

    @classmethod
    def command(
        cls,
        runner: GitRunner,
        args: tuple[str, ...],
        timeout: float = GIT_TIMEOUT,
    ) -> "GitCommand":
        """Run one git command."""
        return cls(lambda: runner.run(*args, timeout=timeout), f"git {args[0]}")

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(
            target=self._run, name=self._name, daemon=True
        )
        self._thread.start()

    def _run(self) -> None:
        self._result = self._task()

    def poll(self) -> Any:
        """Return the result once the work finished, otherwise ``None``."""
        return self._result

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()


# ---------------------------------------------------------------------- #
# 状态解析
# ---------------------------------------------------------------------- #
def parse_status(payload: str) -> StatusSnapshot:
    """Parse ``git status --porcelain=v2 -z --branch`` output.

    The entries are NUL separated. A rename carries its original path as a
    second field, so the token stream has to be walked rather than split
    into lines.
    """
    snapshot = StatusSnapshot()
    tokens = payload.split("\0")
    index = 0
    while index < len(tokens):
        token = tokens[index]
        index += 1
        if not token:
            continue
        if token.startswith("# "):
            _parse_header(token[2:], snapshot)
            continue
        kind = token[0]
        if kind == "1":
            fields = token.split(" ", 8)
            if len(fields) >= 9:
                _record(snapshot, fields[8], fields[1])
        elif kind == "2":
            fields = token.split(" ", 9)
            if len(fields) >= 10:
                # The original path follows as its own NUL terminated field.
                index += 1
                _record(snapshot, fields[9], fields[1])
        elif kind == "u":
            fields = token.split(" ", 10)
            if len(fields) >= 11:
                _record(snapshot, fields[10], fields[1])
        elif kind == "?":
            snapshot.untracked.append(token[2:])
        elif kind == "!":
            continue
    return snapshot


def _parse_header(header: str, snapshot: StatusSnapshot) -> None:
    key, _, value = header.partition(" ")
    if key == "branch.head":
        if value == "(detached)":
            snapshot.detached = True
        else:
            snapshot.branch = value
    elif key == "branch.upstream":
        snapshot.upstream = value
    elif key == "branch.oid":
        # ``(initial)`` marks a repository that has no commit yet.
        if value and value != "(initial)":
            snapshot.oid = value
    elif key == "branch.ab":
        parts = value.split()
        if len(parts) == 2:
            snapshot.ahead = _count(parts[0])
            snapshot.behind = _count(parts[1])


def _count(value: str) -> int:
    try:
        return int(value.lstrip("+-"))
    except ValueError:
        return 0


def _record(snapshot: StatusSnapshot, path: str, code: str) -> None:
    """File one path under the staged and/or unstaged list.

    The two states are judged separately, so a file that is both staged and
    modified again appears in both lists with its own status code.

    Porcelain v2 writes ``.`` where v1 wrote a space to mean "unchanged",
    so both spellings are accepted here.
    """
    index_status = code[0] if code else "."
    worktree_status = code[1] if len(code) > 1 else "."
    if index_status not in (".", " ", "?"):
        snapshot.staged[path] = index_status
    if worktree_status not in (".", " ", "?"):
        snapshot.unstaged[path] = worktree_status


# ---------------------------------------------------------------------- #
# 查询
# ---------------------------------------------------------------------- #
def read_status(runner: GitRunner) -> CommandResult:
    """Collect the file lists and the branch state in one call."""
    return runner.run(
        "status", "--porcelain=v2", "-z", "--branch", timeout=GIT_TIMEOUT
    )


def read_repository_state(
    runner: GitRunner,
) -> tuple[bool, StatusSnapshot | None, CommandResult]:
    """Check whether the folder is a repository and read its state.

    The two commands run back to back so the whole check costs one worker
    thread instead of two. The snapshot is ``None`` when the state could
    not be read; the result then carries the reason.
    """
    inside = runner.run("rev-parse", "--is-inside-work-tree")
    if not inside.ok or inside.stdout.strip() != "true":
        return False, None, inside
    result = read_status(runner)
    if not result.ok:
        return True, None, result
    return True, parse_status(result.stdout), result


def is_safe_branch_name(name: str) -> bool:
    """Whether *name* can be handed to a git command without being read as an option.

    Git itself refuses to create a branch whose name starts with a dash, so
    this only guards the names that come from somewhere else.
    """
    text = name.strip()
    return bool(text) and not text.startswith("-")


def list_branches(runner: GitRunner) -> list[BranchInfo]:
    """Return the local and remote branches of the repository.

    ``git branch --list`` is not used here: its patterns do not match the
    remote branches the way they are shown on screen, and its output is
    not a stable machine format. ``for-each-ref`` states every field
    explicitly.
    """
    result = runner.run(
        "for-each-ref", f"--format={_BRANCH_FORMAT}", "refs/heads/", "refs/remotes/"
    )
    if not result.ok:
        return []
    branches: list[BranchInfo] = []
    for line in result.stdout.splitlines():
        columns = line.split("\t")
        if len(columns) < 4:
            continue
        refname, short, upstream, head = columns[:4]
        if refname.startswith("refs/remotes/"):
            # ``origin/HEAD`` is the symbolic pointer to the default branch,
            # not a branch the user can switch to.
            if refname.endswith("/HEAD"):
                continue
            branches.append(BranchInfo(short, remote=True, upstream=upstream))
        elif refname.startswith("refs/heads/"):
            branches.append(
                BranchInfo(short, current=(head == "*"), upstream=upstream)
            )
    return branches


def validate_branch_name(runner: GitRunner, name: str) -> str:
    """Return the normalised branch name, or an empty string when Git refuses it.

    ``git check-ref-format --branch`` is the authority. It also rejects a
    name that starts with a dash, which would otherwise be read as an
    option by the command that creates it.
    """
    text = name.strip()
    if not text or text.startswith("-") or text == "HEAD" or text.startswith("@{"):
        return ""
    result = runner.run(
        "check-ref-format", "--branch", text, timeout=VALIDATION_TIMEOUT
    )
    if not result.ok:
        return ""
    return result.stdout.strip()


# ---------------------------------------------------------------------- #
# 操作
# ---------------------------------------------------------------------- #
def checkout(runner: GitRunner, name: str) -> CommandResult:
    """Switch to an existing branch."""
    return runner.run("checkout", name, timeout=MUTATION_TIMEOUT)


def create_branch(runner: GitRunner, name: str) -> CommandResult:
    """Create a branch from the current HEAD and switch to it.

    ``--`` is deliberately not used here: ``git checkout -- -b topic``
    switches pathspecs instead of creating a branch.
    """
    return runner.run("checkout", "-b", name, timeout=MUTATION_TIMEOUT)
