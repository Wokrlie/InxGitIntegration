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

    # ------------------------------------------------------------------ #
    # 未初始化仓库的 UI
    # ------------------------------------------------------------------ #
    def _render_no_repo_ui(self, ctx) -> None:
        ctx.label("Source Control")
        ctx.begin_group("Repository")

        ctx.label("This project is not a Git repository yet.")
        ctx.button(
            "Create Git Repository",
            lambda: self.init_git_repo(),
            180.0,
            30.0,
        )

        ctx.end_group()

    # ------------------------------------------------------------------ #
    # 已初始化仓库的 UI（沿用之前的逻辑）
    # ------------------------------------------------------------------ #
    def _render_git_ui(self, ctx) -> None:
        ctx.label("Source Control")
        ctx.begin_group("Changes")

        staged    = [f for f, s in self.files_status_list.items() if s == "2"]
        unstaged  = [f for f, s in self.files_status_list.items() if s == "1"]
        untracked = [f for f, s in self.files_status_list.items() if s == "0"]

        if ctx.collapsing_header(f"Staged Changes ({len(staged)})"):
            if not staged:
                ctx.label("    (none)")
            for f in staged:
                ctx.label(f"    M  {f}")

        if ctx.collapsing_header(f"Changes ({len(unstaged) + len(untracked)})"):
            if not unstaged and not untracked:
                ctx.label("    (none)")
            for f in unstaged:
                ctx.label(f"    M  {f}")
            for f in untracked:
                ctx.label(f"    ?  {f}")

        check_in_msg = ctx.text_input(
            label="",
            value="Message(Press button to commit)",
        )

        ctx.button(
            "Check in staged changes",
            lambda: self.check_in_staged_changes(check_in_msg),
            100.0,
            30.0,
        )

        ctx.end_group()

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
        self.files_status_list.clear()

        # Step 1: 检测当前目录是否在 Git 工作树中
        if not self._is_inside_work_tree():
            self.is_repo_initialized = False
            return

        self.is_repo_initialized = True

        # Step 2: 仅在仓库存在时才执行 git status
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
                self.files_status_list[path] = "0"
                continue

            if index_status not in (" ", "?"):
                self.files_status_list[path] = "2"
            elif worktree_status not in (" ", "?"):
                self.files_status_list[path] = "1"

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
        if not msg or msg == "Message(Press button to commit)":
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
        except FileNotFoundError:
            Debug.error("Git is not installed.")
            return
        except subprocess.TimeoutExpired:
            Debug.error("`git commit` timed out.")
            return

        if result.returncode == 0:
            self.refresh_git_status()
            self._last_refresh = time.time()
        else:
            Debug.error(f"`git commit` failed: {result.stderr.strip()}")