"""Jnotes2Hinote 的桌面图形界面。"""

from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:  # pragma: no cover - exercised only in source installs without extras
    DND_FILES = None
    TkinterDnD = None

from . import CONVERTER_CORE_VERSION, __version__
from .batch import (
    CONFLICT_OVERWRITE,
    CONFLICT_RENAME,
    CONFLICT_SKIP,
    BatchProgress,
    collect_input_files,
    convert_batch,
)

APP_NAME = "Jnotes2Hinote"
LANG_ZH = "zh"
LANG_EN = "en"
CONFIG_FILE_NAME = "gui-settings.json"


TRANSLATIONS: dict[str, dict[str, str]] = {
    LANG_ZH: {
        "title": "Jnotes2Hinote — 云记转华为笔记",
        "subtitle": "将云记 Jnotes 文件转换为华为笔记 Hinote",
        "input_section": "输入文件",
        "add_files": "添加文件",
        "add_folder": "添加文件夹",
        "add_manifest": "添加 TXT 清单",
        "remove_selected": "移除选中",
        "clear": "清空",
        "recursive": "包含子目录中的文件",
        "input_help": "可以混合添加文件、文件夹和 TXT 路径清单，也可以将它们拖到上方列表；相同文件只会转换一次。",
        "output_section": "输出设置",
        "output_dir": "输出目录：",
        "browse": "浏览…",
        "pages": "转换页数：",
        "pages_hint": "0 表示全部页面",
        "conflict": "文件重名：",
        "conflict_rename": "自动添加序号",
        "conflict_skip": "跳过已有文件",
        "conflict_overwrite": "覆盖已有文件",
        "report": "生成 JSON 转换报告",
        "report_path": "报告路径：",
        "report_browse": "选择…",
        "open_output_after": "转换完成后打开输出目录",
        "progress_section": "转换进度",
        "result_section": "文件结果",
        "log_section": "运行日志",
        "clear_log": "清空日志",
        "open_output": "打开输出目录",
        "open_location": "打开所在位置",
        "copy_path": "复制路径",
        "help": "使用说明",
        "start": "开始转换",
        "stop": "停止",
        "language": "语言：",
        "table_type": "类型",
        "table_path": "路径",
        "table_count": "文件数",
        "table_status": "状态",
        "table_source": "源文件",
        "table_output": "输出文件",
        "table_detail": "详情",
        "type_file": "文件",
        "type_folder": "文件夹",
        "type_manifest": "清单",
        "status_pending": "待扫描",
        "status_scanned": "已扫描",
        "status_added": "待处理",
        "status_converted": "成功",
        "status_failed": "失败",
        "status_skipped": "跳过",
        "status_cancelled": "未执行",
        "status_ready": "准备就绪",
        "status_scanning": "正在扫描输入路径…",
        "status_converting": "正在转换…",
        "status_done": "转换完成",
        "status_cancelled_run": "已停止转换",
        "summary_ready": "尚未开始转换",
        "summary_format": "已发现 {total} 个文件，成功 {converted} 个，失败 {failed} 个",
        "current_format": "当前文件：{path}",
        "no_input": "请先添加至少一个输入文件、文件夹或 TXT 清单。",
        "no_output": "请选择输出目录。",
        "invalid_pages": "转换页数必须是大于等于 0 的整数。",
        "output_file_error": "批量转换的输出路径必须是目录，不能使用 .hinote 文件。",
        "output_is_file": "输出路径已经是一个文件，请选择目录。",
        "output_missing": "输出目录还不存在，请先开始转换或选择一个已有目录。",
        "scan_warning_title": "扫描发现问题",
        "scan_warning": "发现 {files} 个可转换文件，另外有 {errors} 个路径无法处理。\n\n是否继续转换可用文件？\n\n{details}",
        "nothing_found_title": "没有可转换文件",
        "nothing_found": "没有找到可转换的 .Jnotes 或 .jnote 文件。\n\n{details}",
        "confirm_clear_title": "清空输入",
        "confirm_clear": "确定要清空当前输入列表吗？",
        "confirm_stop_title": "停止转换",
        "confirm_stop": "当前文件完成后停止转换，可以保留已经生成的文件。是否继续？",
        "running_close_title": "转换正在进行",
        "running_close": "转换尚未完成，确定要退出吗？",
        "done_title": "转换完成",
        "done_message": "成功转换 {converted} 个文件，失败或跳过 {failed} 个。\n\n输出目录：{output}",
        "done_warning_title": "转换完成，但有问题",
        "done_cancelled_title": "转换已停止",
        "done_cancelled": "已完成 {converted} 个文件，尚有 {remaining} 个文件未执行。\n\n输出目录：{output}",
        "fatal_title": "转换失败",
        "fatal": "批量任务无法完成：{error}",
        "add_invalid": "以下路径不是支持的输入类型，已忽略：\n\n{paths}",
        "report_error": "报告写入失败：{error}",
        "about_title": "关于 Jnotes2Hinote",
        "about": "Jnotes2Hinote {version}\n\n将云记 Jnotes 笔记转换为华为笔记 Hinote。\n\n当前转换核心：v{core_version}\n当前项目发行版：v{version}",
        "help_title": "使用说明",
        "help_text": "1. 添加一个或多个 Jnotes 文件、文件夹或 TXT 清单。\n2. 需要搜索子目录时勾选“包含子目录中的文件”。\n3. 选择输出目录和文件重名策略。\n4. 点击“开始转换”，程序会在后台运行并显示进度。\n5. 单个文件失败不会阻止其余文件继续转换。\n\nTXT 清单每行一个路径，空行和以 # 开头的行会被忽略；相对路径以清单所在目录为基准。",
        "log_added": "已添加输入：{path}",
        "log_removed": "已移除 {count} 个输入。",
        "log_scan": "开始扫描 {count} 个输入来源。",
        "log_scan_done": "扫描完成：发现 {files} 个文件，{errors} 个路径有问题。",
        "log_start": "开始转换，共 {total} 个文件。",
        "log_file_success": "成功：{source} → {output}",
        "log_file_failure": "失败：{source}：{error}",
        "log_file_skip": "跳过：{source}：{error}",
        "log_stopping": "已请求停止，将在当前文件完成后停止。",
        "log_finished": "任务结束：成功 {converted}，失败或跳过 {failed}。",
        "log_report": "报告已写入：{path}",
        "log_report_failure": "报告写入失败：{error}",
        "log_open_failed": "无法打开路径：{error}",
    },
    LANG_EN: {
        "title": "Jnotes2Hinote — Jnotes to Huawei Notes",
        "subtitle": "Convert Jnotes notebooks to Huawei Notes Hinote files",
        "input_section": "Input files",
        "add_files": "Add files",
        "add_folder": "Add folder",
        "add_manifest": "Add TXT list",
        "remove_selected": "Remove selected",
        "clear": "Clear",
        "recursive": "Include files in subdirectories",
        "input_help": "Files, folders and TXT path lists can be mixed or dropped onto the list; the same file is converted only once.",
        "output_section": "Output settings",
        "output_dir": "Output directory:",
        "browse": "Browse…",
        "pages": "Pages:",
        "pages_hint": "0 means all pages",
        "conflict": "Name conflicts:",
        "conflict_rename": "Add numeric suffix",
        "conflict_skip": "Skip existing files",
        "conflict_overwrite": "Overwrite existing files",
        "report": "Write JSON conversion report",
        "report_path": "Report path:",
        "report_browse": "Choose…",
        "open_output_after": "Open output directory when finished",
        "progress_section": "Conversion progress",
        "result_section": "File results",
        "log_section": "Run log",
        "clear_log": "Clear log",
        "open_output": "Open output directory",
        "open_location": "Open containing folder",
        "copy_path": "Copy path",
        "help": "Help",
        "start": "Start conversion",
        "stop": "Stop",
        "language": "Language:",
        "table_type": "Type",
        "table_path": "Path",
        "table_count": "Files",
        "table_status": "Status",
        "table_source": "Source",
        "table_output": "Output",
        "table_detail": "Details",
        "type_file": "File",
        "type_folder": "Folder",
        "type_manifest": "List",
        "status_pending": "Pending",
        "status_scanned": "Scanned",
        "status_added": "Pending",
        "status_converted": "Success",
        "status_failed": "Failed",
        "status_skipped": "Skipped",
        "status_cancelled": "Not run",
        "status_ready": "Ready",
        "status_scanning": "Scanning input paths…",
        "status_converting": "Converting…",
        "status_done": "Conversion complete",
        "status_cancelled_run": "Conversion stopped",
        "summary_ready": "Conversion has not started",
        "summary_format": "Found {total} files, converted {converted}, failed {failed}",
        "current_format": "Current file: {path}",
        "no_input": "Add at least one input file, folder or TXT list first.",
        "no_output": "Choose an output directory.",
        "invalid_pages": "Pages must be a non-negative integer.",
        "output_file_error": "Batch output must be a directory, not a .hinote file.",
        "output_is_file": "The output path is already a file. Choose a directory.",
        "output_missing": "The output directory does not exist yet. Start a conversion or choose an existing directory first.",
        "scan_warning_title": "Scan warnings",
        "scan_warning": "Found {files} convertible files, but {errors} paths could not be processed.\n\nContinue with the available files?\n\n{details}",
        "nothing_found_title": "No convertible files",
        "nothing_found": "No .Jnotes or .jnote files were found.\n\n{details}",
        "confirm_clear_title": "Clear inputs",
        "confirm_clear": "Clear the current input list?",
        "confirm_stop_title": "Stop conversion",
        "confirm_stop": "Conversion will stop after the current file. Existing outputs will be kept. Continue?",
        "running_close_title": "Conversion in progress",
        "running_close": "Conversion is still running. Exit anyway?",
        "done_title": "Conversion complete",
        "done_message": "Converted {converted} files successfully; {failed} failed or skipped.\n\nOutput directory: {output}",
        "done_warning_title": "Conversion completed with warnings",
        "done_cancelled_title": "Conversion stopped",
        "done_cancelled": "Completed {converted} files; {remaining} files were not run.\n\nOutput directory: {output}",
        "fatal_title": "Conversion failed",
        "fatal": "The batch task could not complete: {error}",
        "add_invalid": "These paths are not supported input types and were ignored:\n\n{paths}",
        "report_error": "Could not write the report: {error}",
        "about_title": "About Jnotes2Hinote",
        "about": "Jnotes2Hinote {version}\n\nConvert Jnotes notebooks to Huawei Notes Hinote.\n\nConversion core: v{core_version}\nProject release: v{version}",
        "help_title": "Usage",
        "help_text": "1. Add one or more Jnotes files, folders or TXT lists.\n2. Enable subdirectory scanning when needed.\n3. Choose an output directory and a conflict strategy.\n4. Click Start conversion; the task runs in the background.\n5. A failure for one file does not stop the remaining files.\n\nTXT lists contain one path per line. Blank lines and lines beginning with # are ignored; relative paths are resolved next to the list file.",
        "log_added": "Added input: {path}",
        "log_removed": "Removed {count} input(s).",
        "log_scan": "Scanning {count} input source(s).",
        "log_scan_done": "Scan complete: {files} files found, {errors} path issue(s).",
        "log_start": "Starting conversion for {total} file(s).",
        "log_file_success": "Success: {source} → {output}",
        "log_file_failure": "Failed: {source}: {error}",
        "log_file_skip": "Skipped: {source}: {error}",
        "log_stopping": "Stop requested; conversion will stop after the current file.",
        "log_finished": "Task finished: {converted} converted, {failed} failed or skipped.",
        "log_report": "Report written to: {path}",
        "log_report_failure": "Report write failed: {error}",
        "log_open_failed": "Could not open path: {error}",
    },
}


def config_file_path() -> Path:
    """Return a per-user settings path without touching the repository."""

    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif os.environ.get("XDG_CONFIG_HOME"):
        base = Path(os.environ["XDG_CONFIG_HOME"])
    else:
        base = Path.home() / ".config"
    return base / APP_NAME / CONFIG_FILE_NAME


def load_gui_settings() -> dict[str, Any]:
    try:
        return json.loads(config_file_path().read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}


def save_gui_settings(settings: dict[str, Any]) -> None:
    path = config_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")


def open_path(path: Path) -> None:
    if sys.platform == "win32":
        os.startfile(str(path))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def parse_page_limit(value: str) -> int | None:
    number = int(value.strip())
    if number < 0:
        raise ValueError("negative")
    return number or None


def parse_drop_paths(data: str, splitlist: Callable[[str], tuple[str, ...]]) -> tuple[str, ...]:
    """Parse a TkDND file-list payload without breaking paths containing spaces."""

    if not isinstance(data, str) or not data.strip():
        return ()
    try:
        return tuple(path for path in splitlist(data) if path)
    except (tk.TclError, TypeError):
        return ()


def create_root() -> tk.Tk:
    """Create a Tk root with native file-drop support when TkDND is available."""

    if TkinterDnD is not None:
        try:
            return TkinterDnD.Tk()
        except tk.TclError:
            # Keep the button-based workflow usable if a local TkDND binary is missing.
            pass
    return tk.Tk()


class Jnotes2HinoteApp:
    """Tkinter application controller and view."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.settings = load_gui_settings()
        self.language = self.settings.get("language", LANG_ZH)
        if self.language not in TRANSLATIONS:
            self.language = LANG_ZH

        self.sources: list[Path] = []
        self.source_status: dict[str, str] = {}
        self.source_counts: dict[str, int] = {}
        self.event_queue: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.cancel_event = threading.Event()
        self.worker_thread: threading.Thread | None = None
        self.phase = "idle"
        self.pending_files: list[Path] = []
        self.pending_errors: list[dict[str, str]] = []
        self.pending_output = Path()
        self.pending_report: Path | None = None
        self.pending_conflict = self.settings.get("conflict_strategy", CONFLICT_RENAME)
        if self.pending_conflict not in {CONFLICT_RENAME, CONFLICT_SKIP, CONFLICT_OVERWRITE}:
            self.pending_conflict = CONFLICT_RENAME
        self.pending_recursive = False
        self.completed = 0
        self.failed = 0
        self.total = 0

        self.recursive_var = tk.BooleanVar(value=bool(self.settings.get("recursive", False)))
        self.pages_var = tk.StringVar(value=str(self.settings.get("pages", "0")))
        self.output_var = tk.StringVar(value=str(self.settings.get("output", "")))
        self.report_enabled_var = tk.BooleanVar(value=bool(self.settings.get("report_enabled", True)))
        self.report_var = tk.StringVar(value=str(self.settings.get("report", "")))
        self.open_output_var = tk.BooleanVar(value=bool(self.settings.get("open_output", True)))
        self.language_display_var = tk.StringVar()
        self.summary_var = tk.StringVar()
        self.current_var = tk.StringVar()
        self.status_var = tk.StringVar()

        self.text_widgets: dict[str, tk.Widget] = {}
        self.button_widgets: dict[str, ttk.Button] = {}
        self.check_widgets: dict[str, ttk.Checkbutton] = {}
        self.controls: list[tk.Widget] = []

        self._build_ui()
        self._apply_language()
        self._refresh_sources()
        self._set_idle()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(100, self._poll_queue)

    def _t(self, key: str, **values: Any) -> str:
        return TRANSLATIONS[self.language][key].format(**values)

    def _build_ui(self) -> None:
        self.root.title(APP_NAME)
        self.root.minsize(1000, 680)
        geometry = self.settings.get("geometry")
        if isinstance(geometry, str) and geometry:
            try:
                self.root.geometry(geometry)
            except tk.TclError:
                self.root.geometry("1200x760")
        else:
            self.root.geometry("1200x760")

        style = ttk.Style(self.root)
        try:
            style.theme_use("vista" if sys.platform == "win32" else "clam")
        except tk.TclError:
            pass
        style.configure("Accent.TButton", padding=(14, 7))
        style.configure("Status.TLabel", foreground="#555555")
        style.configure("DropHint.TLabel", foreground="#146c2e")

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main = ttk.Frame(self.root, padding=12)
        main.grid(row=0, column=0, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.rowconfigure(1, weight=1)

        header = ttk.Frame(main)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header.columnconfigure(0, weight=1)
        self.text_widgets["title"] = ttk.Label(header, font=("Segoe UI", 16, "bold"))
        self.text_widgets["title"].grid(row=0, column=0, sticky="w")
        self.text_widgets["subtitle"] = ttk.Label(header, style="Status.TLabel")
        self.text_widgets["subtitle"].grid(row=1, column=0, sticky="w", pady=(3, 0))
        header_right = ttk.Frame(header)
        header_right.grid(row=0, column=1, rowspan=2, sticky="e")
        ttk.Label(header_right, text=f"v{__version__}").grid(row=0, column=0, padx=(0, 8))
        self.text_widgets["language"] = ttk.Label(header_right)
        self.text_widgets["language"].grid(row=0, column=1, padx=(0, 5))
        self.language_combo = ttk.Combobox(
            header_right,
            textvariable=self.language_display_var,
            state="readonly",
            width=12,
            values=("简体中文", "English"),
        )
        self.language_combo.grid(row=0, column=2, padx=(0, 8))
        self.language_combo.bind("<<ComboboxSelected>>", self._on_language_changed)
        self.button_widgets["help"] = ttk.Button(header_right, command=self._show_help)
        self.button_widgets["help"].grid(row=0, column=3)

        workspace = ttk.PanedWindow(main, orient="horizontal")
        workspace.grid(row=1, column=0, sticky="nsew", pady=(0, 8))
        left_column = ttk.Frame(workspace)
        left_column.columnconfigure(0, weight=1)
        left_column.rowconfigure(0, weight=1)
        right_column = ttk.Frame(workspace)
        right_column.columnconfigure(0, weight=1)
        right_column.rowconfigure(0, weight=1)
        workspace.add(left_column, weight=1)
        workspace.add(right_column, weight=1)
        self.workspace_pane = workspace

        input_frame = ttk.LabelFrame(left_column)
        input_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        input_frame.columnconfigure(0, weight=1)
        input_frame.rowconfigure(2, weight=1)
        self.text_widgets["input_section"] = input_frame

        input_toolbar = ttk.Frame(input_frame)
        input_toolbar.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        add_actions = (
            ("add_files", self._add_files),
            ("add_folder", self._add_folder),
            ("add_manifest", self._add_manifest),
        )
        manage_actions = (
            ("remove_selected", self._remove_selected),
            ("clear", self._clear_sources),
        )
        for row, actions in enumerate((add_actions, manage_actions)):
            action_frame = ttk.Frame(input_toolbar)
            action_frame.grid(row=row, column=0, sticky="w", pady=(0, 4) if row == 0 else 0)
            for index, (key, command) in enumerate(actions):
                button = ttk.Button(action_frame, command=command)
                button.grid(row=0, column=index, padx=(0, 6))
                self.button_widgets[key] = button

        tree_frame = ttk.Frame(input_frame)
        tree_frame.grid(row=2, column=0, sticky="nsew", padx=8)
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        self.input_drop_target = tree_frame
        self.source_tree = ttk.Treeview(
            tree_frame,
            columns=("type", "path", "count", "status"),
            show="headings",
            selectmode="extended",
            height=10,
        )
        self.source_tree.grid(row=0, column=0, sticky="nsew")
        source_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.source_tree.yview)
        source_scroll.grid(row=0, column=1, sticky="ns")
        source_hscroll = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.source_tree.xview)
        source_hscroll.grid(row=1, column=0, columnspan=2, sticky="ew")
        self.source_tree.configure(yscrollcommand=source_scroll.set, xscrollcommand=source_hscroll.set)
        self.source_tree.bind("<Double-1>", self._open_source_location)
        self.source_tree.bind("<Button-3>", self._show_source_menu)
        self.source_tree.column("type", width=70, minwidth=60, anchor="center", stretch=False)
        self.source_tree.column("path", width=320, minwidth=180, anchor="w")
        self.source_tree.column("count", width=70, minwidth=55, anchor="center", stretch=False)
        self.source_tree.column("status", width=95, minwidth=75, anchor="center", stretch=False)
        self.source_menu = tk.Menu(self.root, tearoff=False)
        self.source_menu.add_command(command=self._open_source_location)
        self.source_menu.add_command(command=self._copy_source_path)
        self.source_menu.add_separator()
        self.source_menu.add_command(command=self._remove_selected)

        input_bottom = ttk.Frame(input_frame)
        input_bottom.grid(row=3, column=0, sticky="ew", padx=8, pady=(7, 8))
        self.check_widgets["recursive"] = ttk.Checkbutton(
            input_bottom,
            variable=self.recursive_var,
            command=self._mark_sources_pending,
        )
        self.check_widgets["recursive"].grid(row=0, column=0, sticky="w")
        self.text_widgets["input_help"] = ttk.Label(input_bottom, style="Status.TLabel", wraplength=500)
        self.text_widgets["input_help"].grid(row=1, column=0, sticky="w", pady=(4, 0))

        output_frame = ttk.LabelFrame(left_column)
        output_frame.grid(row=1, column=0, sticky="ew")
        output_frame.columnconfigure(1, weight=1)
        self.text_widgets["output_section"] = output_frame
        self.text_widgets["output_dir"] = ttk.Label(output_frame)
        self.text_widgets["output_dir"].grid(row=0, column=0, sticky="w", padx=(8, 6), pady=(8, 5))
        self.output_entry = ttk.Entry(output_frame, textvariable=self.output_var)
        self.output_entry.grid(row=0, column=1, sticky="ew", pady=(8, 5))
        self.button_widgets["browse_output"] = ttk.Button(output_frame, command=self._choose_output)
        self.button_widgets["browse_output"].grid(row=0, column=2, padx=(6, 8), pady=(8, 5))
        self.text_widgets["pages"] = ttk.Label(output_frame)
        self.text_widgets["pages"].grid(row=1, column=0, sticky="w", padx=(8, 6), pady=5)
        self.pages_entry = ttk.Entry(output_frame, textvariable=self.pages_var, width=10)
        self.pages_entry.grid(row=1, column=1, sticky="w", pady=5)
        self.text_widgets["pages_hint"] = ttk.Label(output_frame, style="Status.TLabel")
        self.text_widgets["pages_hint"].grid(row=1, column=1, sticky="w", padx=(85, 0), pady=5)
        self.text_widgets["conflict"] = ttk.Label(output_frame)
        self.text_widgets["conflict"].grid(row=2, column=0, sticky="w", padx=(8, 6), pady=5)
        self.conflict_combo = ttk.Combobox(output_frame, state="readonly", width=22)
        self.conflict_combo.grid(row=2, column=1, sticky="w", pady=5)
        self.conflict_combo.bind("<<ComboboxSelected>>", self._on_conflict_changed)
        self.report_check = ttk.Checkbutton(output_frame, variable=self.report_enabled_var, command=self._update_report_state)
        self.report_check.grid(row=3, column=0, columnspan=3, sticky="w", padx=8, pady=5)
        self.check_widgets["report"] = self.report_check
        self.text_widgets["report_path"] = ttk.Label(output_frame)
        self.text_widgets["report_path"].grid(row=4, column=0, sticky="w", padx=(8, 6), pady=(5, 8))
        self.report_entry = ttk.Entry(output_frame, textvariable=self.report_var)
        self.report_entry.grid(row=4, column=1, sticky="ew", pady=(5, 8))
        self.button_widgets["browse_report"] = ttk.Button(output_frame, command=self._choose_report)
        self.button_widgets["browse_report"].grid(row=4, column=2, padx=(6, 8), pady=(5, 8))
        self.check_widgets["open_output_after"] = ttk.Checkbutton(output_frame, variable=self.open_output_var)
        self.check_widgets["open_output_after"].grid(row=5, column=0, columnspan=3, sticky="w", padx=8, pady=(0, 8))

        progress_frame = ttk.LabelFrame(right_column)
        log_frame = ttk.LabelFrame(right_column)
        results_log = ttk.PanedWindow(right_column, orient="vertical")
        results_log.grid(row=0, column=0, sticky="nsew")
        results_log.add(progress_frame, weight=3)
        results_log.add(log_frame, weight=2)
        self.results_log_pane = results_log
        progress_frame.columnconfigure(0, weight=1)
        progress_frame.rowconfigure(1, weight=1)
        self.text_widgets["progress_section"] = progress_frame
        summary_bar = ttk.Frame(progress_frame)
        summary_bar.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 5))
        summary_bar.columnconfigure(0, weight=1)
        self.summary_label = ttk.Label(summary_bar, textvariable=self.summary_var)
        self.summary_label.grid(row=0, column=0, sticky="w")
        self.progress_bar = ttk.Progressbar(summary_bar, mode="determinate", length=220)
        self.progress_bar.grid(row=0, column=1, sticky="e")
        self.current_label = ttk.Label(progress_frame, textvariable=self.current_var, style="Status.TLabel")
        self.current_label.grid(row=2, column=0, sticky="w", padx=8, pady=(5, 8))

        result_frame = ttk.Frame(progress_frame)
        result_frame.grid(row=1, column=0, sticky="nsew", padx=8)
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)
        self.result_tree = ttk.Treeview(
            result_frame,
            columns=("source", "output", "status", "detail"),
            show="headings",
            height=8,
        )
        self.result_tree.grid(row=0, column=0, sticky="nsew")
        result_scroll = ttk.Scrollbar(result_frame, orient="vertical", command=self.result_tree.yview)
        result_scroll.grid(row=0, column=1, sticky="ns")
        result_hscroll = ttk.Scrollbar(result_frame, orient="horizontal", command=self.result_tree.xview)
        result_hscroll.grid(row=1, column=0, columnspan=2, sticky="ew")
        self.result_tree.configure(yscrollcommand=result_scroll.set, xscrollcommand=result_hscroll.set)
        self.result_tree.column("source", width=190, minwidth=150, anchor="w")
        self.result_tree.column("output", width=190, minwidth=150, anchor="w")
        self.result_tree.column("status", width=75, minwidth=65, anchor="center", stretch=False)
        self.result_tree.column("detail", width=190, minwidth=140, anchor="w")
        self.result_tree.tag_configure("converted", foreground="#146c2e")
        self.result_tree.tag_configure("failed", foreground="#a61b1b")
        self.result_tree.tag_configure("skipped", foreground="#8a5a00")

        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        self.text_widgets["log_section"] = log_frame
        self.log_text = tk.Text(log_frame, height=8, wrap="word", state="disabled", undo=False)
        self.log_text.grid(row=0, column=0, sticky="nsew", padx=(8, 0), pady=8)
        log_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        log_scroll.grid(row=0, column=1, sticky="ns", padx=(0, 8), pady=8)
        self.log_text.configure(yscrollcommand=log_scroll.set)

        footer = ttk.Frame(main)
        footer.grid(row=2, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)
        self.status_label = ttk.Label(footer, textvariable=self.status_var, style="Status.TLabel")
        self.status_label.grid(row=0, column=0, sticky="w")
        self.button_widgets["clear_log"] = ttk.Button(footer, command=self._clear_log)
        self.button_widgets["clear_log"].grid(row=0, column=1, padx=(0, 6))
        self.button_widgets["open_output"] = ttk.Button(footer, command=self._open_output)
        self.button_widgets["open_output"].grid(row=0, column=2, padx=(0, 6))
        self.button_widgets["stop"] = ttk.Button(footer, command=self._stop_conversion)
        self.button_widgets["stop"].grid(row=0, column=3, padx=(0, 6))
        self.button_widgets["start"] = ttk.Button(footer, style="Accent.TButton", command=self._start_conversion)
        self.button_widgets["start"].grid(row=0, column=4)

        self.controls = [
            self.button_widgets[key]
            for key in ("add_files", "add_folder", "add_manifest", "remove_selected", "clear", "browse_output", "browse_report")
        ]
        self.controls.extend([
            self.source_tree,
            self.output_entry,
            self.pages_entry,
            self.conflict_combo,
            self.report_check,
            self.report_entry,
            self.check_widgets["recursive"],
            self.check_widgets["open_output_after"],
            self.language_combo,
        ])
        self._setup_drag_and_drop(input_frame)
        self._update_report_state()

    def _setup_drag_and_drop(self, input_frame: ttk.LabelFrame) -> None:
        """Register the input area as a native file-drop target when TkDND is available."""

        self._drop_target_widgets: tuple[tk.Widget, ...] = ()
        self._drop_highlighted = False
        if DND_FILES is None or not hasattr(self.input_drop_target, "drop_target_register"):
            return
        targets = (input_frame, self.input_drop_target, self.source_tree)
        registered: list[tk.Widget] = []
        for widget in targets:
            try:
                widget.drop_target_register(DND_FILES)  # type: ignore[attr-defined]
                widget.dnd_bind("<<DropEnter>>", self._on_drop_enter)  # type: ignore[attr-defined]
                widget.dnd_bind("<<DropPosition>>", self._on_drop_position)  # type: ignore[attr-defined]
                widget.dnd_bind("<<DropLeave>>", self._on_drop_leave)  # type: ignore[attr-defined]
                widget.dnd_bind("<<Drop>>", self._on_drop)  # type: ignore[attr-defined]
                registered.append(widget)
            except tk.TclError:
                continue
        self._drop_target_widgets = tuple(registered)

    def _on_drop_enter(self, _event: tk.Event) -> str:
        if self.phase != "idle":
            return "refuse_drop"
        self._drop_highlighted = True
        self.text_widgets["input_help"].configure(style="DropHint.TLabel")
        return "copy"

    def _on_drop_position(self, _event: tk.Event) -> str:
        return "copy" if self.phase == "idle" else "refuse_drop"

    def _on_drop_leave(self, _event: tk.Event) -> None:
        self._drop_highlighted = False
        self.text_widgets["input_help"].configure(style="Status.TLabel")

    def _on_drop(self, event: tk.Event) -> str:
        self._on_drop_leave(event)
        if self.phase != "idle":
            return "refuse_drop"
        data = getattr(event, "data", "")
        paths = parse_drop_paths(data, self.root.tk.splitlist)
        if paths:
            self._add_paths(paths)
        return "copy"

    def _apply_language(self) -> None:
        self.root.title(self._t("title"))
        for key, widget in self.text_widgets.items():
            if key != "report":
                widget.configure(text=self._t(key))
        for key, widget in self.button_widgets.items():
            if key in {"browse_output", "browse_report"}:
                widget.configure(text=self._t("browse" if key == "browse_output" else "report_browse"))
            else:
                widget.configure(text=self._t(key))
        for key, widget in self.check_widgets.items():
            widget.configure(text=self._t(key))
        if hasattr(self, "help_menu"):
            self.help_menu.entryconfigure(0, label=self._t("help"))
            self.help_menu.entryconfigure(1, label=self._t("about_title"))
            self.main_menu.entryconfigure(0, label=self._t("help"))
        if hasattr(self, "source_menu"):
            self.source_menu.entryconfigure(0, label=self._t("open_location"))
            self.source_menu.entryconfigure(1, label=self._t("copy_path"))
            self.source_menu.entryconfigure(3, label=self._t("remove_selected"))
        headings = {
            "type": "table_type",
            "path": "table_path",
            "count": "table_count",
            "status": "table_status",
        }
        for column, key in headings.items():
            self.source_tree.heading(column, text=self._t(key))
        result_headings = {"source": "table_source", "output": "table_output", "status": "table_status", "detail": "table_detail"}
        for column, key in result_headings.items():
            self.result_tree.heading(column, text=self._t(key))
        self.language_display_var.set("简体中文" if self.language == LANG_ZH else "English")
        self._set_conflict_display()
        self._refresh_sources()
        self._refresh_summary()
        self._update_report_state()

    def _set_conflict_display(self) -> None:
        values = [
            self._t("conflict_rename"),
            self._t("conflict_skip"),
            self._t("conflict_overwrite"),
        ]
        self.conflict_combo["values"] = values
        labels = {
            CONFLICT_RENAME: values[0],
            CONFLICT_SKIP: values[1],
            CONFLICT_OVERWRITE: values[2],
        }
        self.conflict_combo.set(labels.get(self.pending_conflict, values[0]))

    def _on_language_changed(self, _event: tk.Event) -> None:
        self.language = LANG_EN if self.language_combo.current() == 1 else LANG_ZH
        self._apply_language()

    def _on_conflict_changed(self, _event: tk.Event) -> None:
        index = self.conflict_combo.current()
        self.pending_conflict = (CONFLICT_RENAME, CONFLICT_SKIP, CONFLICT_OVERWRITE)[max(0, index)]

    def _source_type_key(self, path: Path) -> str:
        if path.is_dir() or (not path.exists() and path.suffix.lower() not in {".txt", ".jnotes", ".jnote"}):
            return "type_folder"
        if path.suffix.lower() == ".txt":
            return "type_manifest"
        return "type_file"

    def _refresh_sources(self) -> None:
        for item in self.source_tree.get_children():
            self.source_tree.delete(item)
        for index, path in enumerate(self.sources):
            key = str(path)
            count = self.source_counts.get(key, "")
            self.source_tree.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    self._t(self._source_type_key(path)),
                    str(path),
                    count,
                    self.source_status.get(key, self._t("status_added")),
                ),
            )

    def _add_paths(self, paths: list[str] | tuple[str, ...]) -> None:
        invalid: list[str] = []
        added = 0
        for raw_path in paths:
            path = Path(raw_path).expanduser()
            supported = path.is_dir() or path.suffix.lower() in {".txt", ".jnotes", ".jnote"}
            if not supported:
                invalid.append(str(path))
                continue
            if path not in self.sources:
                self.sources.append(path)
                self.source_status[str(path)] = self._t("status_added")
                added += 1
                self._append_log(self._t("log_added", path=path))
        self._refresh_sources()
        if invalid:
            messagebox.showwarning(self._t("scan_warning_title"), self._t("add_invalid", paths="\n".join(invalid)), parent=self.root)
        if added:
            self.status_var.set(self._t("status_ready"))

    def _add_files(self) -> None:
        paths = filedialog.askopenfilenames(
            parent=self.root,
            title=self._t("add_files"),
            filetypes=[("Jnotes files", "*.Jnotes *.jnote"), ("All files", "*.*")],
        )
        self._add_paths(paths)

    def _add_folder(self) -> None:
        path = filedialog.askdirectory(parent=self.root, title=self._t("add_folder"))
        if path:
            self._add_paths([path])

    def _add_manifest(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.root,
            title=self._t("add_manifest"),
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if path:
            self._add_paths([path])

    def _remove_selected(self) -> None:
        selected = sorted((int(item) for item in self.source_tree.selection()), reverse=True)
        for index in selected:
            if 0 <= index < len(self.sources):
                self.sources.pop(index)
        if selected:
            self._append_log(self._t("log_removed", count=len(selected)))
            self._refresh_sources()

    def _clear_sources(self) -> None:
        if self.sources and not messagebox.askyesno(self._t("confirm_clear_title"), self._t("confirm_clear"), parent=self.root):
            return
        self.sources.clear()
        self.source_status.clear()
        self.source_counts.clear()
        self._refresh_sources()
        self.status_var.set(self._t("status_ready"))

    def _mark_sources_pending(self) -> None:
        for path in self.sources:
            self.source_status[str(path)] = self._t("status_pending")
        self.source_counts.clear()
        self._refresh_sources()

    def _choose_output(self) -> None:
        path = filedialog.askdirectory(parent=self.root, title=self._t("output_dir"))
        if path:
            self.output_var.set(path)
            if not self.report_var.get().strip():
                self.report_var.set(str(Path(path) / "conversion_report.json"))

    def _choose_report(self) -> None:
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title=self._t("report_browse"),
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if path:
            self.report_var.set(path)
            self.report_enabled_var.set(True)
            self._update_report_state()

    def _update_report_state(self) -> None:
        state = "normal" if self.report_enabled_var.get() and self.phase == "idle" else "disabled"
        self.report_entry.configure(state=state)
        self.button_widgets["browse_report"].configure(state=state)

    def _open_source_location(self, _event: tk.Event | None = None) -> None:
        item = self.source_tree.selection()[0] if self.source_tree.selection() else ""
        if not item:
            return
        path = Path(self.source_tree.item(item, "values")[1])
        target = path if path.is_dir() else path.parent
        try:
            open_path(target)
        except OSError as exc:
            messagebox.showerror(self._t("fatal_title"), self._t("log_open_failed", error=exc), parent=self.root)

    def _show_source_menu(self, event: tk.Event) -> str:
        item = self.source_tree.identify_row(event.y)
        if not item:
            return "break"
        self.source_tree.selection_set(item)
        self.source_menu.tk_popup(event.x_root, event.y_root)
        self.source_menu.grab_release()
        return "break"

    def _copy_source_path(self) -> None:
        selected = self.source_tree.selection()
        if not selected:
            return
        path = self.source_tree.item(selected[0], "values")[1]
        self.root.clipboard_clear()
        self.root.clipboard_append(path)

    def _validate_start(self) -> tuple[Path, int | None] | None:
        if not self.sources:
            messagebox.showwarning(self._t("scan_warning_title"), self._t("no_input"), parent=self.root)
            return None
        output_text = self.output_var.get().strip()
        if not output_text:
            messagebox.showwarning(self._t("scan_warning_title"), self._t("no_output"), parent=self.root)
            return None
        output = Path(output_text).expanduser()
        if output.exists() and not output.is_dir():
            messagebox.showerror(self._t("fatal_title"), self._t("output_is_file"), parent=self.root)
            return None
        if output.suffix.lower() == ".hinote" and not output.exists():
            messagebox.showerror(self._t("fatal_title"), self._t("output_file_error"), parent=self.root)
            return None
        try:
            page_limit = parse_page_limit(self.pages_var.get())
        except (ValueError, TypeError):
            messagebox.showwarning(self._t("scan_warning_title"), self._t("invalid_pages"), parent=self.root)
            return None
        return output, page_limit

    def _start_conversion(self) -> None:
        if self.phase != "idle":
            return
        validated = self._validate_start()
        if validated is None:
            return
        output, page_limit = validated
        self.pending_output = output
        self.pending_report = None
        if self.report_enabled_var.get():
            report_text = self.report_var.get().strip()
            self.pending_report = Path(report_text).expanduser() if report_text else output / "conversion_report.json"
            self.report_var.set(str(self.pending_report))
        self.pending_conflict = self.pending_conflict or CONFLICT_RENAME
        self.pending_page_limit = page_limit
        self.pending_recursive = self.recursive_var.get()
        self.pending_files = []
        self.pending_errors = []
        self.source_counts.clear()
        self.cancel_event.clear()
        self.completed = 0
        self.failed = 0
        self.total = 0
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)
        self._set_running("scanning")
        self.status_var.set(self._t("status_scanning"))
        self._append_log(self._t("log_scan", count=len(self.sources)))
        self.worker_thread = threading.Thread(
            target=self._scan_worker,
            args=(list(self.sources), self.pending_recursive),
            daemon=True,
        )
        self.worker_thread.start()

    def _scan_worker(self, sources: list[Path], recursive: bool) -> None:
        counts: dict[str, int] = {}
        try:
            files, errors = collect_input_files(
                sources,
                recursive=recursive,
                source_counts=counts,
            )
            self.event_queue.put(("scan_complete", (files, errors, counts)))
        except Exception as exc:  # noqa: BLE001 - worker boundary must report every failure to the GUI
            self.event_queue.put(("fatal", exc))

    def _begin_conversion(self) -> None:
        self.phase = "converting"
        self.status_var.set(self._t("status_converting"))
        self.total = len(self.pending_files)
        self.progress_bar.configure(maximum=max(self.total, 1), value=0)
        self.summary_var.set(self._t("summary_format", total=self.total, converted=0, failed=len(self.pending_errors)))
        self.current_var.set(self._t("current_format", path="—"))
        self._append_log(self._t("log_start", total=self.total))
        self.worker_thread = threading.Thread(target=self._convert_worker, daemon=True)
        self.worker_thread.start()

    def _convert_worker(self) -> None:
        try:
            summary = convert_batch(
                self.pending_files,
                self.pending_output,
                page_limit=self.pending_page_limit,
                recursive=self.pending_recursive,
                conflict_strategy=self.pending_conflict,
                initial_errors=self.pending_errors,
                progress_callback=lambda update: self.event_queue.put(("progress", update)),
                cancel_event=self.cancel_event,
            )
            report_error = None
            if self.pending_report is not None:
                try:
                    self.pending_report.parent.mkdir(parents=True, exist_ok=True)
                    self.pending_report.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
                except OSError as exc:
                    report_error = str(exc)
            self.event_queue.put(("done", (summary, report_error)))
        except Exception as exc:  # noqa: BLE001 - worker boundary must report every failure to the GUI
            self.event_queue.put(("fatal", exc))

    def _poll_queue(self) -> None:
        try:
            while True:
                kind, payload = self.event_queue.get_nowait()
                if kind == "scan_complete":
                    self._handle_scan_complete(*payload)
                elif kind == "progress":
                    self._handle_progress(payload)
                elif kind == "done":
                    self._handle_done(*payload)
                elif kind == "fatal":
                    self._handle_fatal(payload)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_queue)

    def _handle_scan_complete(
        self,
        files: list[Path],
        errors: list[dict[str, str]],
        counts: dict[str, int],
    ) -> None:
        self.source_counts = counts
        for path in self.sources:
            key = str(path)
            self.source_status[key] = self._t("status_scanned")
        self._refresh_sources()
        self._append_log(self._t("log_scan_done", files=len(files), errors=len(errors)))
        if self.cancel_event.is_set():
            self._finish_cancelled(0, len(files))
            return
        if not files:
            details = "\n".join(f"{item['path']}: {item['error']}" for item in errors[:12])
            self._set_idle()
            messagebox.showerror(self._t("nothing_found_title"), self._t("nothing_found", details=details), parent=self.root)
            return
        if errors:
            details = "\n".join(f"{item['path']}: {item['error']}" for item in errors[:12])
            if len(errors) > 12:
                details += f"\n… ({len(errors) - 12} more)"
            proceed = messagebox.askyesno(
                self._t("scan_warning_title"),
                self._t("scan_warning", files=len(files), errors=len(errors), details=details),
                parent=self.root,
            )
            if not proceed:
                self._set_idle()
                return
        self.pending_files = files
        self.pending_errors = errors
        self._begin_conversion()

    def _handle_progress(self, update: BatchProgress) -> None:
        self.progress_bar.configure(value=update.index)
        self.current_var.set(self._t("current_format", path=str(update.source)))
        if update.status == "converted":
            self.completed += 1
            self.result_tree.insert(
                "",
                "end",
                values=(str(update.source), str(update.output or ""), self._t("status_converted"), ""),
                tags=("converted",),
            )
            self._append_log(self._t("log_file_success", source=update.source, output=update.output))
        elif update.status == "failed":
            self.failed += 1
            self.result_tree.insert(
                "",
                "end",
                values=(str(update.source), str(update.output or ""), self._t("status_failed"), update.error or ""),
                tags=("failed",),
            )
            self._append_log(self._t("log_file_failure", source=update.source, error=update.error or ""))
        elif update.status == "skipped":
            self.failed += 1
            self.result_tree.insert(
                "",
                "end",
                values=(str(update.source), "", self._t("status_skipped"), update.error or ""),
                tags=("skipped",),
            )
            self._append_log(self._t("log_file_skip", source=update.source, error=update.error or ""))
        self._refresh_summary()

    def _handle_done(self, summary: dict[str, Any], report_error: str | None) -> None:
        self.completed = int(summary.get("converted", 0))
        self.failed = int(summary.get("failed", 0))
        self._refresh_summary()
        self._append_log(self._t("log_finished", converted=self.completed, failed=self.failed))
        if self.pending_report is not None and report_error is None:
            self._append_log(self._t("log_report", path=self.pending_report))
        elif report_error:
            self._append_log(self._t("log_report_failure", error=report_error))
        was_cancelled = bool(summary.get("cancelled"))
        self._set_idle()
        if was_cancelled:
            remaining = max(0, self.total - self.completed - self.failed)
            self.status_var.set(self._t("status_cancelled_run"))
            messagebox.showwarning(
                self._t("done_cancelled_title"),
                self._t("done_cancelled", converted=self.completed, remaining=remaining, output=self.pending_output),
                parent=self.root,
            )
            return
        self.status_var.set(self._t("status_done"))
        if self.open_output_var.get() and self.pending_output.exists():
            try:
                open_path(self.pending_output)
            except OSError as exc:
                self._append_log(self._t("log_open_failed", error=exc))
        title = self._t("done_title") if self.failed == 0 else self._t("done_warning_title")
        messagebox.showinfo(
            title,
            self._t("done_message", converted=self.completed, failed=self.failed, output=self.pending_output),
            parent=self.root,
        )

    def _handle_fatal(self, error: Exception) -> None:
        self._set_idle()
        self.status_var.set(self._t("status_failed"))
        self._append_log(self._t("fatal", error=error))
        messagebox.showerror(self._t("fatal_title"), self._t("fatal", error=error), parent=self.root)

    def _finish_cancelled(self, converted: int, remaining: int) -> None:
        self._set_idle()
        self.status_var.set(self._t("status_cancelled_run"))
        messagebox.showwarning(
            self._t("done_cancelled_title"),
            self._t("done_cancelled", converted=converted, remaining=remaining, output=self.pending_output),
            parent=self.root,
        )

    def _refresh_summary(self) -> None:
        if self.total:
            self.summary_var.set(self._t("summary_format", total=self.total, converted=self.completed, failed=self.failed))
        else:
            self.summary_var.set(self._t("summary_ready"))

    def _set_running(self, phase: str) -> None:
        self.phase = phase
        for widget in self.controls:
            try:
                widget.configure(state="disabled")
            except tk.TclError:
                pass
        self.source_tree.state(["disabled"])
        self.button_widgets["start"].configure(state="disabled")
        self.button_widgets["stop"].configure(state="normal")
        self.button_widgets["clear_log"].configure(state="disabled")
        self.button_widgets["open_output"].configure(state="disabled")
        self._update_report_state()

    def _set_idle(self) -> None:
        self.phase = "idle"
        for widget in self.controls:
            try:
                widget.configure(state="normal")
            except tk.TclError:
                pass
        self.source_tree.state(["!disabled"])
        self.button_widgets["start"].configure(state="normal")
        self.button_widgets["stop"].configure(state="disabled")
        self.button_widgets["clear_log"].configure(state="normal")
        self.button_widgets["open_output"].configure(state="normal")
        self._update_report_state()

    def _stop_conversion(self) -> None:
        if self.phase == "idle":
            return
        if not messagebox.askyesno(self._t("confirm_stop_title"), self._t("confirm_stop"), parent=self.root):
            return
        self.cancel_event.set()
        self.button_widgets["stop"].configure(state="disabled")
        self._append_log(self._t("log_stopping"))

    def _append_log(self, message: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", message.rstrip() + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _clear_log(self) -> None:
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def _open_output(self) -> None:
        raw = self.output_var.get().strip()
        if not raw:
            messagebox.showwarning(self._t("scan_warning_title"), self._t("no_output"), parent=self.root)
            return
        path = Path(raw).expanduser()
        if not path.exists():
            messagebox.showwarning(self._t("scan_warning_title"), self._t("output_missing"), parent=self.root)
            return
        try:
            open_path(path)
        except OSError as exc:
            self._append_log(self._t("log_open_failed", error=exc))

    def _show_help(self) -> None:
        messagebox.showinfo(self._t("help_title"), self._t("help_text"), parent=self.root)

    def _show_about(self) -> None:
        messagebox.showinfo(
            self._t("about_title"),
            self._t("about", version=__version__, core_version=CONVERTER_CORE_VERSION),
            parent=self.root,
        )

    def _save_settings(self) -> None:
        try:
            save_gui_settings(
                {
                    "language": self.language,
                    "recursive": self.recursive_var.get(),
                    "pages": self.pages_var.get(),
                    "output": self.output_var.get(),
                    "report_enabled": self.report_enabled_var.get(),
                    "report": self.report_var.get(),
                    "open_output": self.open_output_var.get(),
                    "conflict_strategy": self.pending_conflict,
                    "geometry": self.root.geometry(),
                }
            )
        except OSError:
            pass

    def _on_close(self) -> None:
        if self.phase != "idle":
            if not messagebox.askyesno(self._t("running_close_title"), self._t("running_close"), parent=self.root):
                return
            self.cancel_event.set()
        self._save_settings()
        self.root.destroy()


def main() -> None:
    root = create_root()
    app = Jnotes2HinoteApp(root)
    root.option_add("*tearoff", False)
    menu = tk.Menu(root)
    help_menu = tk.Menu(menu, tearoff=False)
    help_menu.add_command(label=app._t("help"), command=app._show_help)
    help_menu.add_command(label=app._t("about_title"), command=app._show_about)
    menu.add_cascade(label=app._t("help"), menu=help_menu)
    app.main_menu = menu
    app.help_menu = help_menu
    root.configure(menu=menu)
    root.mainloop()


if __name__ == "__main__":
    main()
