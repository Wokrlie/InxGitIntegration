"""Git panel available only inside the editor."""

from __future__ import annotations

import os
import time

from infernux import Debug
from infernux.engine.i18n import t
from infernux.engine.interaction import PanelInteractionDescriptor
from infernux.engine.project_context import get_project_root
from infernux.engine.ui.editor_panel import EditorPanel
from infernux.engine.ui.panel_registry import editor_panel
from infernux.engine.ui.theme import ImGuiCol

from .git import (
    BranchInfo,
    CommandResult,
    GitCommand,
    GitRunner,
    StatusSnapshot,
    checkout,
    commit,
    create_branch,
    delete_branch,
    init_repository,
    is_safe_branch_name,
    read_repository_state,
    rename_branch,
    stage_all,
    stage_file,
    unstage_file,
)
from .icons import IconCache, NEUTRAL_COLOR, STATUS_COLORS, STATUS_LABELS


#: Longest branch name shown in the header before it is shortened.
_MAX_BRANCH_LABEL = 28
#: Dimmed colour for secondary text such as the upstream of a branch.
_DIM_COLOR = (0.55, 0.55, 0.58, 1.0)
#: Colour of the branch name while HEAD is detached.
_DETACHED_COLOR = (0.95, 0.55, 0.20, 1.0)
#: ImGui's ``ImGuiCond_FirstUseEver``. A section opens the first time the
#: user sees it and then keeps whatever state they leave it in.
_FIRST_USE = 4


@editor_panel(
    "Git Integration",
    type_id="wokrlie.git_integration",
    title_key="wokrlie.git_integration.panel_title",
    menu_path="Extensions/Git Integration",
    menu_path_keys=(
        "menu.extensions",
        "wokrlie.git_integration.menu_root",
    ),
    interaction=PanelInteractionDescriptor(),
)
class GitIntegrationPanel(EditorPanel):
    """Source control panel backed by the ``git`` command line.

    Every git command runs on a worker thread. The render thread only
    draws the last snapshot it received, so a slow repository never
    freezes the Editor.
    """

    #: Tag for the Console entries this plugin writes. The Engine groups and
    #: clears entries by source, so the plugin's diagnostics stay separable
    #: from everyone else's.
    SOURCE_FILE = "wokrlie/git_integration/panel.py"

    def __init__(self) -> None:
        super().__init__("Git Integration", "wokrlie.git_integration.panel")

        self.have_git: bool = False
        self.is_repo_initialized: bool = False

        self._snapshot = StatusSnapshot()
        self._state_known: bool = False
        self._status_command: GitCommand | None = None
        self._action_command: GitCommand | None = None
        self._action_report: bool = False
        self._action_on_success = None

        self._branches: list[BranchInfo] = []
        self._branch_filter: str = ""
        self._new_branch: str = ""
        self._selected_branch: str = ""
        self._rename_open: bool = False
        self._rename_name: str = ""

        self._error: str = ""
        self._error_detail: str = ""
        self._error_shown: bool = False
        self._copy_requested: bool = False

        self._commit_message: str = ""
        self._last_refresh: float = 0.0
        self._refresh_interval: float = 1.0

        self._icons: IconCache | None = None
        self._icon_size: float = 16.0
        self._button_size: float = 18.0

    # ------------------------------------------------------------------ #
    # 生命周期（保持惰性初始化，避免 on_enable 崩溃）
    # ------------------------------------------------------------------ #
    def on_enable(self) -> None:
        self.have_git = False
        self.is_repo_initialized = False
        self._snapshot = StatusSnapshot()
        self._state_known = False
        self._status_command = None
        self._action_command = None
        self._branches = []
        self._branch_filter = ""
        self._new_branch = ""
        self._selected_branch = ""
        self._rename_open = False
        self._rename_name = ""
        self._error = ""
        self._error_detail = ""
        self._error_shown = False
        self._last_refresh = 0.0

    @property
    def repo_path(self) -> str:
        """The folder the panel operates on.

        Prefers the project root the Editor currently has open and falls back
        to the process working directory when no project is loaded. Resolved on
        every read so switching projects does not leave a stale path behind.
        """
        return get_project_root() or os.getcwd()

    def _runner(self) -> GitRunner:
        """A runner bound to the folder the panel currently works on."""
        return GitRunner(self.repo_path)

    # ------------------------------------------------------------------ #
    # 日志（写入引擎 Console）
    # ------------------------------------------------------------------ #
    def _log_error(self, message: str) -> None:
        """Write one error to the Editor Console.

        The Console keeps the entry after the panel closes, so a long Git
        message stays readable and can be copied from there. A panel popup
        only points the user here; it is not the place where the error
        survives.
        """
        Debug.log_error(message, source_file=self.SOURCE_FILE)

    # ------------------------------------------------------------------ #
    # 图标（Lucide SVG → 运行时光栅化 → ImGui 纹理）
    # ------------------------------------------------------------------ #
    def _icon_cache(self) -> IconCache | None:
        """Return the icon cache, creating it once the renderer is reachable."""
        if self._icons is None:
            try:
                services = self.services
                native = services.native_engine if services is not None else None
            except Exception:  # noqa: BLE001 - the panel must never fail to open
                native = None
            if native is None:
                return None
            self._icons = IconCache(native)
        return self._icons

    def _icon(self, name: str, color=NEUTRAL_COLOR) -> int:
        """Return the ImGui texture id for one icon, or ``0`` when unavailable."""
        cache = self._icon_cache()
        if cache is None:
            return 0
        return cache.get(name, color)

    def _status_icon(self, status: str) -> int:
        """Return the ImGui texture id for a git porcelain status code."""
        cache = self._icon_cache()
        if cache is None:
            return 0
        return cache.status_icon(status)

    def _tooltip(self, ctx, text: str) -> None:
        """Show *text* as a tooltip for the widget that was just rendered."""
        if ctx.is_item_hovered():
            ctx.set_tooltip(text)

    def _icon_button(self, ctx, widget_id: str, icon: str, tooltip: str, on_click) -> None:
        """Render one icon button, with a tooltip, when its texture exists.

        ``image_button`` silently does nothing while the texture is still
        uploading, so the button and its tooltip are skipped together. That
        keeps the tooltip attached to the right widget instead of drifting
        onto the previous one.
        """
        texture = self._icon(icon)
        if not texture:
            return
        if ctx.image_button(widget_id, texture, self._button_size, self._button_size):
            on_click()
        self._tooltip(ctx, tooltip)

    # ------------------------------------------------------------------ #
    # 渲染主流程
    # ------------------------------------------------------------------ #
    def on_render_content(self, ctx) -> None:
        self._poll_background()
        self._schedule_status()

        if not self._state_known:
            # The first status call has not answered yet. Whether git is
            # usable at all is answered by the same call.
            return

        if not self.have_git:
            ctx.label(t("wokrlie.git_integration.git_unavailable"))
            return

        if not self.is_repo_initialized:
            self._render_no_repo_ui(ctx)          # 未初始化仓库：只显示创建按钮
            return

        self._render_git_ui(ctx)                  # 已初始化仓库：正常 Git 操作界面

    def _render_no_repo_ui(self, ctx) -> None:
        """Render the view shown when the folder is not a Git repository yet."""
        ctx.label(t("wokrlie.git_integration.not_a_repository"))
        ctx.button(
            f"{t('wokrlie.git_integration.create_repository')}##create_repository",
            self.init_git_repo,
            240.0,
            28.0,
        )
        ctx.label(
            f"{t('wokrlie.git_integration.repository_folder')}: {self.repo_path}"
        )

    def _render_git_ui(self, ctx) -> None:
        ctx.label(t("wokrlie.git_integration.source_control"))
        ctx.same_line()
        self._icon_button(
            ctx,
            "##refresh_git",
            "refresh",
            t("wokrlie.git_integration.refresh"),
            self._manual_refresh,
        )

        self._render_branches_section(ctx)

        ctx.begin_group("Changes")
        try:
            self._render_staged_section(ctx)
            self._render_changes_section(ctx)

            # -------- 提交消息 --------
            ctx.label(t("wokrlie.git_integration.commit_message"))
            ctx.set_next_item_width(380.0)
            self._commit_message = ctx.text_input(
                label="##commit_msg",
                value=self._commit_message,      # ← 持久状态，不再用提示字面量
            )

            # -------- 提交按钮 --------
            commit_msg = self._commit_message
            ctx.button(
                t("wokrlie.git_integration.commit"),
                lambda: self.check_in_staged_changes(commit_msg),
                380.0,                            # ← 加宽，避免文字被截断
                30.0,
            )
        finally:
            ctx.end_group()

        self._render_error_dialog(ctx)

    # ------------------------------------------------------------------ #
    # 分支
    # ------------------------------------------------------------------ #
    def _render_branches_section(self, ctx) -> None:
        """The branch section: the current branch, the list, and the new row.

        The branches live in their own section instead of behind a popup:
        the list is the thing the user works with, and a popup hid it
        behind one click.
        """
        ctx.set_next_item_open(True, _FIRST_USE)
        if not ctx.collapsing_header(
            f"{t('wokrlie.git_integration.branches')} ({len(self._branches)})###branches"
        ):
            return

        self._render_current_branch(ctx)
        ctx.separator()

        ctx.set_next_item_width(280.0)
        self._branch_filter = ctx.input_text_with_hint(
            "##git_branch_filter",
            t("wokrlie.git_integration.branch_filter"),
            self._branch_filter,
            128,
        )

        labels, entries = self._visible_branches()
        if labels:
            clicked = ctx.selectable_list_clipped(labels)
            if 0 <= clicked < len(entries):
                self._select_branch(entries[clicked])
        else:
            ctx.label(t("wokrlie.git_integration.no_branches"))

        ctx.separator()
        self._render_branch_actions(ctx)
        ctx.separator()
        self._render_create_branch(ctx)

    def _select_branch(self, branch: BranchInfo) -> None:
        """Remember which branch the actions below the list apply to.

        The list does not switch on a click any more: the actions need a
        target, and the branch the project is on cannot be deleted.
        """
        if self._selected_branch == branch.name:
            return
        self._selected_branch = branch.name
        self._rename_open = False
        self._rename_name = ""

    def _render_branch_actions(self, ctx) -> None:
        """The actions that apply to the selected branch."""
        name = self._selected_branch
        if not name:
            ctx.label(t("wokrlie.git_integration.select_a_branch"))
            return

        ctx.label(f"{t('wokrlie.git_integration.selected_branch')}: {name}")

        ctx.button(
            t("wokrlie.git_integration.checkout"),
            lambda: self._checkout_selected(name),
            90.0,
            0.0,
        )
        ctx.same_line()
        ctx.button(
            t("wokrlie.git_integration.rename"),
            self._open_rename,
            90.0,
            0.0,
        )
        ctx.same_line()
        ctx.button(
            t("wokrlie.git_integration.delete"),
            lambda: self._delete_branch(name, False),
            90.0,
            0.0,
        )
        ctx.same_line()
        ctx.button(
            t("wokrlie.git_integration.force_delete"),
            lambda: self._delete_branch(name, True),
            110.0,
            0.0,
        )
        self._tooltip(ctx, t("wokrlie.git_integration.force_delete_hint"))

        if self._rename_open:
            self._render_rename_row(ctx, name)

    def _render_rename_row(self, ctx, name: str) -> None:
        """The row that renames the selected branch."""
        ctx.set_next_item_width(200.0)
        self._rename_name = ctx.input_text_with_hint(
            "##git_rename_branch",
            t("wokrlie.git_integration.rename_to"),
            self._rename_name,
            128,
        )
        ctx.same_line()
        ctx.button(
            t("wokrlie.git_integration.rename"),
            lambda: self._rename_branch(name),
            90.0,
            0.0,
        )
        ctx.same_line()
        ctx.button(
            t("wokrlie.git_integration.cancel"),
            self._close_rename,
            90.0,
            0.0,
        )

    def _open_rename(self) -> None:
        """Show the row that renames the selected branch."""
        self._rename_open = True

    def _close_rename(self) -> None:
        """Hide the rename row again."""
        self._rename_open = False
        self._rename_name = ""

    def _checkout_selected(self, name: str) -> None:
        """Switch to the selected branch."""
        for branch in self._branch_rows():
            if branch.name == name:
                self._switch_to(branch)
                return
        self._report_failure(
            t("wokrlie.git_integration.error_branch_missing"), name
        )

    def _rename_branch(self, name: str) -> None:
        """Rename the selected branch."""
        new_name = self._rename_name.strip()
        if not new_name:
            self._report_failure(
                t("wokrlie.git_integration.error_invalid_name"),
                "A new branch name is needed.",
            )
            return
        runner = self._runner()
        self._start_action(
            lambda: rename_branch(runner, name, new_name), report=True
        )
        self._close_rename()

    def _delete_branch(self, name: str, force: bool) -> None:
        """Delete the selected branch."""
        runner = self._runner()
        self._start_action(
            lambda: delete_branch(runner, name, force), report=True
        )

    def _render_current_branch(self, ctx) -> None:
        """The branch the project is on, with its upstream and its drift."""
        icon = self._icon("git-branch")
        if icon:
            ctx.image(icon, self._icon_size, self._icon_size)
            ctx.same_line()

        name = self._branch_label()
        detached = self._snapshot.detached
        if detached:
            ctx.push_style_color(ImGuiCol.Text, *_DETACHED_COLOR)
        ctx.label(name)
        if detached:
            ctx.pop_style_color()
        self._tooltip(ctx, self._branch_tooltip())

        if self._snapshot.upstream:
            ctx.same_line()
            ctx.push_style_color(ImGuiCol.Text, *_DIM_COLOR)
            ctx.label(self._upstream_label())
            ctx.pop_style_color()

    def _branch_label(self) -> str:
        """The branch name shown in the header."""
        if self._snapshot.detached:
            return t("wokrlie.git_integration.detached_head")
        name = self._snapshot.branch
        if not name:
            return t("wokrlie.git_integration.no_branch")
        if len(name) > _MAX_BRANCH_LABEL:
            return name[: _MAX_BRANCH_LABEL - 1] + "…"
        return name

    def _branch_tooltip(self) -> str:
        """The full branch name, for when the header shortens it."""
        if self._snapshot.detached:
            label = t("wokrlie.git_integration.detached_head")
            sha = self._snapshot.oid[:7]
            return f"{label} {sha}" if sha else label
        return self._snapshot.branch or t("wokrlie.git_integration.no_branch")

    def _upstream_label(self) -> str:
        """The upstream of the current branch and how far it drifted."""
        text = self._snapshot.upstream
        if self._snapshot.ahead or self._snapshot.behind:
            text = f"{text}  ↑{self._snapshot.ahead} ↓{self._snapshot.behind}"
        return text

    def _visible_branches(self) -> tuple[list[str], list[BranchInfo]]:
        """The branch rows that pass the filter, with the branch behind each."""
        needle = self._branch_filter.strip().casefold()
        labels: list[str] = []
        entries: list[BranchInfo] = []
        for branch in self._branch_rows():
            if needle and needle not in branch.name.casefold():
                continue
            marker = ""
            if branch.name == self._selected_branch:
                marker += "▸"
            if branch.current:
                marker += "●"
            label = f"{marker} {branch.name}" if marker else branch.name
            if branch.upstream:
                label = f"{label}    {branch.upstream}"
            labels.append(label)
            entries.append(branch)
        return labels, entries

    def _branch_rows(self) -> list[BranchInfo]:
        """Every branch to offer, with the current one always present.

        A repository without any commit has no branch ref yet, so the
        current branch has to be added by hand.
        """
        branches = list(self._branches)
        current = self._snapshot.branch
        if current and not any(
            branch.name == current and not branch.remote for branch in branches
        ):
            branches.insert(0, BranchInfo(current, current=True))
        return branches

    def _render_create_branch(self, ctx) -> None:
        """The row that creates a branch from the current HEAD."""
        ctx.set_next_item_width(280.0)
        self._new_branch = ctx.input_text_with_hint(
            "##git_new_branch",
            t("wokrlie.git_integration.new_branch_name"),
            self._new_branch,
            128,
        )
        ctx.same_line()
        ctx.button(
            t("wokrlie.git_integration.create_branch"),
            self._create_branch,
            110.0,
            0.0,
        )

    def _switch_to(self, branch: BranchInfo) -> None:
        """Start a switch to another branch."""
        if branch.current:
            return
        if not is_safe_branch_name(branch.name):
            self._report_failure(
                t("wokrlie.git_integration.error_invalid_name"),
                f"`git checkout {branch.name}` is not a valid branch name.",
            )
            return
        name = branch.name
        runner = self._runner()
        self._start_action(lambda: checkout(runner, name), report=True)

    def _create_branch(self) -> None:
        """Create a branch from the current HEAD and switch to it."""
        name = self._new_branch.strip()
        if not name:
            self._report_failure(
                t("wokrlie.git_integration.error_invalid_name"),
                "A branch name is needed.",
            )
            return
        runner = self._runner()
        self._start_action(lambda: create_branch(runner, name), report=True)

    # ------------------------------------------------------------------ #
    # 文件列表
    # ------------------------------------------------------------------ #
    def _render_file_row(self, ctx, path: str, status: str, staged: bool) -> None:
        """Render one file row: status icon, path, coloured code, action button.

        The status code keeps its Git spelling so that a dual state such as
        ``AM`` stays readable, and it is coloured by the kind of change. The
        leading icon repeats that meaning as a shape, which is what carries
        the meaning when the code is hard to spot in a dense list.
        """
        icon = self._status_icon(status)
        if icon:
            ctx.image(icon, self._icon_size, self._icon_size)
            ctx.same_line()

        ctx.label(path)
        ctx.same_line()

        color = STATUS_COLORS.get(status, NEUTRAL_COLOR)
        ctx.push_style_color(ImGuiCol.Text, *color)
        ctx.label(status)
        ctx.pop_style_color()
        label_key = STATUS_LABELS.get(status)
        if label_key:
            self._tooltip(ctx, t(label_key))
        ctx.same_line()

        if staged:
            self._icon_button(
                ctx,
                f"##unstage_{path}",
                "unstage",
                t("wokrlie.git_integration.unstage_file"),
                lambda p=path: self.unstage_file(p),
            )
        else:
            self._icon_button(
                ctx,
                f"##stage_{path}",
                "stage",
                t("wokrlie.git_integration.stage_file"),
                lambda p=path: self.stage_file(p),
            )

    def _render_staged_section(self, ctx) -> None:
        staged = self._snapshot.staged
        expanded = ctx.collapsing_header(
            f"{t('wokrlie.git_integration.staged_changes')} "
            f"({len(staged)})###staged_changes"
        )
        if not expanded:
            return

        if not staged:
            ctx.label(f"    {t('wokrlie.git_integration.none')}")
            return

        for path, status in sorted(staged.items()):
            self._render_file_row(ctx, path, status, staged=True)

    def _render_changes_section(self, ctx) -> None:
        unstaged = self._snapshot.unstaged
        untracked = self._snapshot.untracked
        total = len(unstaged) + len(untracked)
        expanded = ctx.collapsing_header(
            f"{t('wokrlie.git_integration.changes')} ({total})###changes"
        )

        # Stage all 放到 header 下一行，避免 same_line 遮挡点击区域
        if total > 0:
            stage_all_icon = self._icon("stage-all")
            if stage_all_icon:
                ctx.image(stage_all_icon, self._icon_size, self._icon_size)
                ctx.same_line()
            ctx.button(
                f"{t('wokrlie.git_integration.stage_all')}##stage_all",
                self.stage_all,
                120.0,
                22.0,
            )

        if not expanded:
            return

        if total == 0:
            ctx.label(f"    {t('wokrlie.git_integration.none')}")
            return

        for path, status in sorted(unstaged.items()):
            self._render_file_row(ctx, path, status, staged=False)

        for path in sorted(untracked):
            self._render_file_row(ctx, path, "?", staged=False)

    # ------------------------------------------------------------------ #
    # Git 可用性检测（与仓库检测分离）
    # ------------------------------------------------------------------ #
    def _report_git_missing(self) -> None:
        """Record that git could not be started at all."""
        self.have_git = False
        self._log_error("Git is not usable in current environment.")

    # ------------------------------------------------------------------ #
    # 后台执行
    # ------------------------------------------------------------------ #
    def _schedule_status(self) -> None:
        """Start a status refresh when the previous one is done and due."""
        if self._status_command is not None or self._action_command is not None:
            return
        if self._state_known and not self.have_git:
            # Git could not be started. Trying again would only spawn a
            # process that cannot start.
            return
        now = time.time()
        if now - self._last_refresh < self._refresh_interval:
            return
        self._last_refresh = now
        self._start_status_refresh()

    def _start_status_refresh(self) -> None:
        """Ask the worker thread for the current repository state."""
        if self._status_command is not None:
            return
        runner = self._runner()
        self._status_command = GitCommand(
            lambda: read_repository_state(runner), "git status"
        )
        self._status_command.start()

    def _start_action(
        self,
        job,
        report: bool = False,
        on_success=None,
    ) -> None:
        """Start one mutating git job in the background.

        *job* is a callable that runs the command and returns its
        result. It runs on a worker thread, so it must not touch the
        Engine API: the runner it needs is captured on the render thread
        before the job is handed over.

        *report* turns a failure into the modal dialog; the routine
        operations only write to the Console.
        """
        if self._action_command is not None:
            return
        self._action_report = report
        self._action_on_success = on_success
        self._action_command = GitCommand(job, "git action")
        self._action_command.start()

    def _poll_background(self) -> None:
        """Apply the results of the background work that finished."""
        action = self._action_command
        if action is not None:
            result = action.poll()
            if result is not None:
                self._action_command = None
                self._finish_action(result)

        status = self._status_command
        if status is not None:
            state = status.poll()
            if state is not None:
                self._status_command = None
                self._apply_state(state)

    def _apply_state(self, state) -> None:
        """Store the repository state the worker thread reported."""
        self._state_known = True
        self.have_git = state.available
        self.is_repo_initialized = state.inside
        if state.snapshot is not None:
            self._snapshot = state.snapshot
        if state.inside:
            self._branches = state.branches
        elif not state.available:
            self._report_git_missing()
        elif state.error is not None:
            self._log_error(f"`git status` failed: {state.error.summary}")

    def _finish_action(self, result: CommandResult) -> None:
        """Apply the outcome of a mutating command."""
        if result.ok:
            if self._action_on_success is not None:
                self._action_on_success()
                self._action_on_success = None
            self._after_mutation()
            return

        detail = (result.stderr or result.stdout).strip()
        self._log_error(self._failure_report(result, detail))
        if self._action_report:
            self._error = self._describe_failure(result)
            self._error_detail = detail

    def _failure_report(self, result: CommandResult, detail: str) -> str:
        """The full failure text, as the Console keeps it.

        The command line, the exit code, and Git's own message all belong
        here. The dialog in the panel only points at this entry, so this is
        the one place where the reason survives.
        """
        command = result.command or "git"
        headline = f"`{command}` failed with exit code {result.returncode}"
        return f"{headline}:\n{detail}" if detail else headline

    def _after_mutation(self) -> None:
        """Ask for a fresh state after a mutating command finished."""
        self._last_refresh = 0.0

    def _describe_failure(self, result: CommandResult) -> str:
        """Turn a git failure into a message the user can act on.

        The wording of git's own messages differs between versions — an
        older git says ``Cannot delete branch 'x' checked out at ...``
        where a newer one says ``cannot delete branch 'x' used by
        worktree at ...`` — so the text is matched in lower case.
        """
        text = f"{result.stderr}\n{result.stdout}"
        lowered = text.lower()
        if "would be overwritten by checkout" in lowered:
            return t("wokrlie.git_integration.error_local_changes")
        if "not fully merged" in lowered:
            return t("wokrlie.git_integration.error_branch_not_merged")
        if "delete branch" in lowered:
            return t("wokrlie.git_integration.error_delete_current")
        if "pathspec" in lowered or "did not match any file" in lowered:
            return t("wokrlie.git_integration.error_branch_missing")
        if "not found" in lowered:
            return t("wokrlie.git_integration.error_branch_missing")
        if "not a valid branch name" in lowered:
            return t("wokrlie.git_integration.error_invalid_name")
        if "already exists" in lowered:
            return t("wokrlie.git_integration.error_branch_exists")
        if "already used by worktree" in lowered:
            return t("wokrlie.git_integration.error_worktree")
        return t("wokrlie.git_integration.error_generic")

    # ------------------------------------------------------------------ #
    # 错误弹窗（Console 留档 + 弹窗指路）
    # ------------------------------------------------------------------ #
    def _report_failure(self, summary: str, detail: str = "") -> None:
        """Show a failure in the panel and keep the full text in the Console."""
        self._log_error(detail or summary)
        self._error = summary
        self._error_detail = detail or summary

    def _render_error_dialog(self, ctx) -> None:
        """The dialog that points at the Console for the full message."""
        if not self._error:
            return

        title = t("wokrlie.git_integration.operation_failed")
        if not self._error_shown:
            # Keep asking until ImGui accepts the request: a one frame
            # request can be lost during focus arbitration.
            ctx.open_popup(title)

        if not ctx.begin_popup_modal(title):
            if self._error_shown:
                # The user closed the modal.
                self._error_shown = False
                self._error = ""
                self._error_detail = ""
            return

        self._error_shown = True
        try:
            ctx.text_wrapped(self._error)
            ctx.text_wrapped(t("wokrlie.git_integration.error_see_console"))
            ctx.separator()
            ctx.button(
                t("wokrlie.git_integration.open_console"),
                self._open_console,
                150.0,
                0.0,
            )
            ctx.same_line()
            ctx.button(
                t("wokrlie.git_integration.copy_details"),
                self._request_copy,
                150.0,
                0.0,
            )
            ctx.same_line()
            ctx.button(
                t("wokrlie.git_integration.close"),
                self._dismiss_error,
                90.0,
                0.0,
            )
            if self._copy_requested:
                self._copy_requested = False
                ctx.set_clipboard_text(self._error_detail)
        finally:
            ctx.end_popup()

    def _open_console(self) -> None:
        """Focus the Engine Console so the full message can be read there."""
        try:
            services = self.services
            manager = services.window_manager if services is not None else None
            if manager is None:
                return
            manager.open_window("console")
            manager.focus_window("console")
        except Exception as exc:  # noqa: BLE001 - the panel must never fail
            self._log_error(f"Cannot open the Console: {exc}")

    def _request_copy(self) -> None:
        """Ask for the error text to be copied to the clipboard."""
        self._copy_requested = True

    def _dismiss_error(self) -> None:
        """Close the error dialog."""
        self._error = ""
        self._error_detail = ""

    # ------------------------------------------------------------------ #
    # 仓库操作
    # ------------------------------------------------------------------ #
    def init_git_repo(self) -> None:
        """在当前项目目录初始化一个新的 Git 仓库。"""
        folder = self.repo_path
        if not os.path.isdir(folder):
            self._log_error(
                f"Cannot initialise a repository in a missing folder: {folder}"
            )
            return
        self._start_action(lambda: init_repository(self._runner()))

    def check_in_staged_changes(self, msg: str) -> None:
        if not msg or not msg.strip():
            self._log_error("Commit message is empty.")
            return

        if not self.is_repo_initialized:
            self._log_error("No Git repository. Please create one first.")
            return

        message = msg
        runner = self._runner()
        self._start_action(
            lambda: commit(runner, message),
            on_success=self._clear_commit_message,
        )

    def _clear_commit_message(self) -> None:
        """Empty the message box after a successful commit, as VS Code does."""
        self._commit_message = ""

    def stage_file(self, path: str) -> None:
        """暂存单个文件（包括新增、修改、删除）。

        使用 ``--`` 分隔符避免路径被误当作选项；对已删除文件，`git add <path>`
        同样会记录删除操作（Git 2.x 起）。
        """
        if not self.is_repo_initialized:
            return
        runner = self._runner()
        self._start_action(lambda: stage_file(runner, path))

    def stage_all(self) -> None:
        """暂存所有变更（等价于 `git add -A`，包含修改、新增和删除）。"""
        if not self.is_repo_initialized:
            return
        runner = self._runner()
        self._start_action(lambda: stage_all(runner))

    def unstage_file(self, path: str) -> None:
        if not self.is_repo_initialized:
            return
        runner = self._runner()
        self._start_action(lambda: unstage_file(runner, path))

    # ------------------------------------------------------------------ #
    # 刷新辅助
    # ------------------------------------------------------------------ #
    def _manual_refresh(self) -> None:
        self._last_refresh = 0.0
