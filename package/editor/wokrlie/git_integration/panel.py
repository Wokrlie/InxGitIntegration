"""Example panel available only inside the editor."""

from infernux.engine.interaction import PanelInteractionDescriptor
from infernux.engine.ui.editor_panel import EditorPanel
from infernux.engine.ui.panel_registry import editor_panel
from infernux import Debug
import subprocess, time, os

@editor_panel(
    "Git integration",
    type_id="wokrlie.git_integration",
    title_key="wokrlie.git_panel",
    menu_path="Extensions/Git Integration",
    menu_path_keys=(
        "menu.extensions",
        "wokrlie.git_integration.menu_root",
    ),
    interaction=PanelInteractionDescriptor(),
)


class GitIntegrationPanel(EditorPanel):
    def __init__(self) -> None:
        super().__init__("Git Integration", "wokrlie.git_integration.panel")

        self.have_git: bool = False
        self.is_repo_initialized: bool = False
        self.files_status_list: dict[str, str] = {}

        self._commit_message: str = ""
        self._last_refresh: float = 0.0
        self._refresh_interval: float = 1.0
        self._git_checked: bool = False

        # 项目根目录，优先从引擎获取，否则回退到当前工作目录
        self.repo_path: str = os.getcwd()

    # ------------------------------------------------------------------ #
    # 生命周期（保持惰性初始化，避免 on_enable 崩溃）
    # ------------------------------------------------------------------ #
    def on_enable(self) -> None:
        self._git_checked = False
        self.have_git = False
        self.is_repo_initialized = False

    def on_render_content(self, ctx) -> None:
        if not self._git_checked:
            self._check_git_availability()
            self._git_checked = True

        if not self.have_git:
            ctx.label("Git is not usable in current environment.")
            return

        # 节流刷新仓库状态
        now = time.time()
        if now - self._last_refresh >= self._refresh_interval:
            self.refresh_git_status()
            self._last_refresh = now

        # ==================== 分支渲染 ====================
        if not self.is_repo_initialized:
            self._render_no_repo_ui(ctx)          # 未初始化仓库：只显示创建按钮
            return

        self._render_git_ui(ctx)                  # 已初始化仓库：正常 Git 操作界面
        # ===================================================

    def _render_git_ui(self, ctx) -> None:
        ctx.label("Source Control")
        ctx.same_line()
        ctx.button("⟳##refresh_git", self._manual_refresh, 28.0, 20.0)

        ctx.begin_group("Changes")
        try:
            self._render_staged_section(ctx)
            self._render_changes_section(ctx)

            # -------- 提交消息 --------
            ctx.label("Commit message:")
            self._try_set_next_item_width(ctx, 380.0)
            self._commit_message = ctx.text_input(
                label="##commit_msg",
                value=self._commit_message,      # ← 持久状态，不再用提示字面量
            )

            # -------- 提交按钮 --------
            commit_msg = self._commit_message
            ctx.button(
                "Check in staged changes",
                lambda: self.check_in_staged_changes(commit_msg),
                380.0,                            # ← 加宽，避免文字被截断
                30.0,
            )
        finally:
            ctx.end_group()


    def _try_set_next_item_width(self, ctx, width: float) -> None:
        """ImGui 的 SetNextItemWidth 若已绑定则使用，否则降级为默认宽度。"""
        try:
            ctx.set_next_item_width(width)
        except (AttributeError, TypeError):
            pass


    def _render_staged_section(self, ctx) -> None:
        expanded = ctx.collapsing_header(f"Staged Changes ({len(self.staged_files)})")
        if not expanded:
            return

        if not self.staged_files:
            ctx.label("    (none)")
            return

        for path, status in sorted(self.staged_files.items()):
            ctx.label(f"    {status}  {path}")
            ctx.same_line()
            ctx.button(
                f"-##unstage_{path}",
                lambda p=path: self.unstage_file(p),
                20.0,
                18.0,
            )


    def _render_changes_section(self, ctx) -> None:
        total = len(self.unstaged_files) + len(self.untracked_files)
        expanded = ctx.collapsing_header(f"Changes ({total})")

        # Stage all 放到 header 下一行，避免 same_line 遮挡点击区域
        if total > 0:
            ctx.button(
                "Stage all##stage_all",
                self.stage_all,
                120.0,
                22.0,
            )

        if not expanded:
            return

        if total == 0:
            ctx.label("    (none)")
            return

        for path, status in sorted(self.unstaged_files.items()):
            ctx.label(f"    {status}  {path}")
            ctx.same_line()
            ctx.button(
                f"+##stage_{path}",
                lambda p=path: self.stage_file(p),
                20.0,
                18.0,
            )

        for path in sorted(self.untracked_files):
            ctx.label(f"    ?  {path}")
            ctx.same_line()
            ctx.button(
                f"+##stage_{path}",
                lambda p=path: self.stage_file(p),
                20.0,
                18.0,
            )

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
            Debug.error("Git is not usable in current environment.")

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
            Debug.error(f"`git status` failed: {exc}")
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
        try:
            result = subprocess.run(
                ["git", "init"],
                capture_output=True,
                text=True,
                cwd=self.repo_path,
                timeout=10,
            )
        except FileNotFoundError:
            Debug.error("Git is not installed.")
            return
        except subprocess.TimeoutExpired:
            Debug.error("`git init` timed out.")
            return

        if result.returncode == 0:
            # 初始化成功后立即刷新状态，面板会切换到"已初始化"分支
            self.refresh_git_status()
            self._last_refresh = time.time()
        else:
            Debug.error(f"`git init` failed: {result.stderr.strip()}")

    # ------------------------------------------------------------------ #
    # 提交（仅在有仓库时可用）
    # ------------------------------------------------------------------ #
    def check_in_staged_changes(self, msg: str) -> None:
        if not msg or not msg.strip():
            Debug.error("Commit message is empty.")
            return

        if not self.is_repo_initialized:
            Debug.error("No Git repository. Please create one first.")
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
            Debug.error(f"`git commit` failed: {exc}")
            return

        if result.returncode == 0:
            self._commit_message = ""       # 成功后清空，符合 VSCode 习惯
            self._refresh_after_mutation()
        else:
            # 常见失败：没有 staged changes / user.name 未配置 / 钩子拒绝
            Debug.error(f"`git commit` failed: {result.stderr.strip()}")

    def stage_file(self, path: str) -> None:
        """暂存单个文件（包括新增、修改、删除）。

        使用 ``--`` 分隔符避免路径被误当作选项；对已删除文件，`git add <path>`
        同样会记录删除操作（Git 2.x 起）。
        """
        if not self.is_repo_initialized:
            Debug.error("No Git repository. Please create one first.")
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
            Debug.error(f"`git add` failed: {exc}")
            return

        if result.returncode == 0:
            self._refresh_after_mutation()
        else:
            Debug.error(f"`git add {path}` failed: {result.stderr.strip()}")


    def stage_all(self) -> None:
        """暂存所有变更（等价于 `git add -A`，包含修改、新增和删除）。"""
        if not self.is_repo_initialized:
            Debug.error("No Git repository. Please create one first.")
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
            Debug.error(f"`git add -A` failed: {exc}")
            return

        if result.returncode == 0:
            self._refresh_after_mutation()
        else:
            Debug.error(f"`git add -A` failed: {result.stderr.strip()}")


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
            Debug.error(f"unstage failed: {fallback.stderr.strip()}")


    def _refresh_after_mutation(self) -> None:
        """任何 stage/unstage/commit 之后调用，立即刷新状态并重置节流计时。"""
        self.refresh_git_status()
        self._last_refresh = time.time()

    def _manual_refresh(self) -> None:
        self.refresh_git_status()
        self._last_refresh = time.monotonic()