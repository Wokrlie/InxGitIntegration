"""Git panel available only inside the editor."""

from __future__ import annotations

import os
import subprocess
import time

from infernux import Debug
from infernux.engine.i18n import t
from infernux.engine.interaction import PanelInteractionDescriptor
from infernux.engine.project_context import get_project_root
from infernux.engine.ui.editor_panel import EditorPanel
from infernux.engine.ui.panel_registry import editor_panel
from infernux.engine.ui.theme import ImGuiCol

from .icons import IconCache, NEUTRAL_COLOR, STATUS_COLORS, STATUS_LABELS


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
    """Source control panel backed by the ``git`` command line."""

    #: Tag for the Console entries this plugin writes. The Engine groups and
    #: clears entries by source, so the plugin's diagnostics stay separable
    #: from everyone else's.
    SOURCE_FILE = "wokrlie/git_integration/panel.py"

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

    def __init__(self) -> None:
        super().__init__("Git Integration", "wokrlie.git_integration.panel")

        self.have_git: bool = False
        self.is_repo_initialized: bool = False

        # ``staged_files``/``unstaged_files`` map a path to its porcelain status
        # code. A path may appear in both when it has staged *and* unstaged
        # content (for example the ``AM`` state).
        self.staged_files: dict[str, str] = {}
        self.unstaged_files: dict[str, str] = {}
        self.untracked_files: list[str] = []

        self._commit_message: str = ""
        self._last_refresh: float = 0.0
        self._refresh_interval: float = 1.0
        self._git_checked: bool = False

        self._icons: IconCache | None = None
        self._icon_size: float = 16.0
        self._button_size: float = 18.0

    # ------------------------------------------------------------------ #
    # 生命周期（保持惰性初始化，避免 on_enable 崩溃）
    # ------------------------------------------------------------------ #
    def on_enable(self) -> None:
        self._git_checked = False
        self.have_git = False
        self.is_repo_initialized = False
        self.staged_files = {}
        self.unstaged_files = {}
        self.untracked_files = []

    @property
    def repo_path(self) -> str:
        """The folder the panel operates on.

        Prefers the project root the Editor currently has open and falls back
        to the process working directory when no project is loaded. Resolved on
        every read so switching projects does not leave a stale path behind.
        """
        return get_project_root() or os.getcwd()

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

    def on_render_content(self, ctx) -> None:
        if not self._git_checked:
            self._check_git_availability()
            self._git_checked = True

        if not self.have_git:
            ctx.label(t("wokrlie.git_integration.git_unavailable"))
            return

        # 节流刷新仓库状态
        now = time.time()
        if now - self._last_refresh >= self._refresh_interval:
            self.refresh_git_status()
            self._last_refresh = now

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
        expanded = ctx.collapsing_header(
            f"{t('wokrlie.git_integration.staged_changes')} "
            f"({len(self.staged_files)})###staged_changes"
        )
        if not expanded:
            return

        if not self.staged_files:
            ctx.label(f"    {t('wokrlie.git_integration.none')}")
            return

        for path, status in sorted(self.staged_files.items()):
            self._render_file_row(ctx, path, status, staged=True)

    def _render_changes_section(self, ctx) -> None:
        total = len(self.unstaged_files) + len(self.untracked_files)
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

        for path, status in sorted(self.unstaged_files.items()):
            self._render_file_row(ctx, path, status, staged=False)

        for path in sorted(self.untracked_files):
            self._render_file_row(ctx, path, "?", staged=False)

    # ------------------------------------------------------------------ #
    # Git 可用性检测（与仓库检测分离）
    # ------------------------------------------------------------------ #
    def _check_git_availability(self) -> None:
        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            self.have_git = result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            self.have_git = False

        if not self.have_git:
            self._log_error("Git is not usable in current environment.")

    # ------------------------------------------------------------------ #
    # 刷新：先检测仓库是否存在，再拉取文件状态
    # ------------------------------------------------------------------ #
    def refresh_git_status(self) -> None:
        """Run `git status --porcelain` and rebuild the three file lists.

        - ``AM path`` 这类文件会**同时**出现在 staged 和 unstaged 两个列表中，
        与 `git status` / VSCode 的显示一致。
        """
        staged:    dict[str, str] = {}
        unstaged:  dict[str, str] = {}
        untracked: list[str]      = []

        if not self._is_inside_work_tree():
            self.is_repo_initialized = False
            self.staged_files = {}
            self.unstaged_files = {}
            self.untracked_files = []
            return

        self.is_repo_initialized = True

        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=True,
                cwd=self.repo_path,
                timeout=5,
            )
        except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            self._log_error(f"`git status` failed: {exc}")
            return

        for raw in result.stdout.splitlines():
            if len(raw) < 4:
                continue

            index_status    = raw[0]
            worktree_status = raw[1]
            path            = raw[3:].strip()

            if " -> " in path:
                path = path.split(" -> ", 1)[1]

            if index_status == "?" and worktree_status == "?":
                untracked.append(path)
                continue

            if index_status == "!" and worktree_status == "!":
                continue

            # 关键：X 和 Y 独立判断，不再互斥
            if index_status not in (" ", "?"):
                staged[path] = index_status
            if worktree_status not in (" ", "?"):
                unstaged[path] = worktree_status

        self.staged_files = staged
        self.unstaged_files = unstaged
        self.untracked_files = untracked

    def _is_inside_work_tree(self) -> bool:
        """使用 `git rev-parse --is-inside-work-tree` 判断是否在 Git 工作树中。"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                capture_output=True,
                text=True,
                cwd=self.repo_path,
                timeout=5,
            )
            return result.returncode == 0 and result.stdout.strip() == "true"
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    # ------------------------------------------------------------------ #
    # 初始化仓库
    # ------------------------------------------------------------------ #
    def init_git_repo(self) -> None:
        """在当前项目目录初始化一个新的 Git 仓库。"""
        folder = self.repo_path
        if not os.path.isdir(folder):
            self._log_error(f"Cannot initialise a repository in a missing folder: {folder}")
            return

        try:
            result = subprocess.run(
                ["git", "init"],
                capture_output=True,
                text=True,
                cwd=folder,
                timeout=10,
            )
        except FileNotFoundError:
            self._log_error("Git is not installed.")
            return
        except subprocess.TimeoutExpired:
            self._log_error("`git init` timed out.")
            return

        if result.returncode == 0:
            # 初始化成功后立即刷新状态，面板会切换到"已初始化"分支
            self.refresh_git_status()
            self._last_refresh = time.time()
        else:
            self._log_error(f"`git init` failed: {result.stderr.strip()}")

    # ------------------------------------------------------------------ #
    # 提交（仅在有仓库时可用）
    # ------------------------------------------------------------------ #
    def check_in_staged_changes(self, msg: str) -> None:
        if not msg or not msg.strip():
            self._log_error("Commit message is empty.")
            return

        if not self.is_repo_initialized:
            self._log_error("No Git repository. Please create one first.")
            return

        try:
            result = subprocess.run(
                ["git", "commit", "-m", msg],
                capture_output=True,
                text=True,
                cwd=self.repo_path,
                timeout=10,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            self._log_error(f"`git commit` failed: {exc}")
            return

        if result.returncode == 0:
            self._commit_message = ""       # 成功后清空，符合 VSCode 习惯
            self._refresh_after_mutation()
        else:
            # 常见失败：没有 staged changes / user.name 未配置 / 钩子拒绝
            self._log_error(f"`git commit` failed: {result.stderr.strip()}")

    def stage_file(self, path: str) -> None:
        """暂存单个文件（包括新增、修改、删除）。

        使用 ``--`` 分隔符避免路径被误当作选项；对已删除文件，`git add <path>`
        同样会记录删除操作（Git 2.x 起）。
        """
        if not self.is_repo_initialized:
            self._log_error("No Git repository. Please create one first.")
            return

        try:
            result = subprocess.run(
                ["git", "add", "--", path],
                capture_output=True,
                text=True,
                cwd=self.repo_path,
                timeout=10,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            self._log_error(f"`git add` failed: {exc}")
            return

        if result.returncode == 0:
            self._refresh_after_mutation()
        else:
            self._log_error(f"`git add {path}` failed: {result.stderr.strip()}")

    def stage_all(self) -> None:
        """暂存所有变更（等价于 `git add -A`，包含修改、新增和删除）。"""
        if not self.is_repo_initialized:
            self._log_error("No Git repository. Please create one first.")
            return

        try:
            result = subprocess.run(
                ["git", "add", "-A"],
                capture_output=True,
                text=True,
                cwd=self.repo_path,
                timeout=10,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            self._log_error(f"`git add -A` failed: {exc}")
            return

        if result.returncode == 0:
            self._refresh_after_mutation()
        else:
            self._log_error(f"`git add -A` failed: {result.stderr.strip()}")

    def unstage_file(self, path: str) -> None:
        if not self.is_repo_initialized:
            return

        # 尝试1: 标准情况 (有 HEAD 时可用)
        # 使用 `git reset HEAD -- <path>` 是 VS Code 的主要方式
        result = subprocess.run(
            ["git", "reset", "HEAD", "--", path],
            capture_output=True, text=True, cwd=self.repo_path, timeout=10,
        )
        if result.returncode == 0:
            self._refresh_after_mutation()
            return

        # 尝试2: 无提交历史 (No commits yet) 的回退
        # 不指定 HEAD，直接清空该路径的暂存条目
        fallback = subprocess.run(
            ["git", "reset", "--", path],
            capture_output=True, text=True, cwd=self.repo_path, timeout=10,
        )
        if fallback.returncode == 0:
            self._refresh_after_mutation()
        else:
            self._log_error(f"unstage failed: {fallback.stderr.strip()}")

    # ------------------------------------------------------------------ #
    # 刷新辅助
    # ------------------------------------------------------------------ #
    def _refresh_after_mutation(self) -> None:
        """任何 stage/unstage/commit 之后调用，立即刷新状态并重置节流计时。"""
        self.refresh_git_status()
        self._last_refresh = time.time()

    def _manual_refresh(self) -> None:
        self.refresh_git_status()
        self._last_refresh = time.time()
