"""Huawei-to-Jnotes desktop app using the same layout as the forward tool."""

from typing import ClassVar

from jnotes2hinote.gui import LANG_EN, LANG_ZH, TRANSLATIONS, Jnotes2HinoteApp, run_gui

from .batch import INPUT_SUFFIXES, collect_input_files, convert_batch
from .writer import OUTPUT_SUFFIXES

APP_NAME = "Hinote2Jnotes"
REVERSE_TRANSLATIONS = {
    LANG_ZH: {
        **TRANSLATIONS[LANG_ZH],
        "title": "Hinote2Jnotes — 华为笔记转云记",
        "subtitle": "将华为笔记 Hinote 文件转换为云记 Jnotes",
        "output_file_error": "批量转换的输出路径必须是目录，不能使用 .Jnotes 或 .jnote 文件。",
        "nothing_found": "没有找到可转换的 .hinote 或 .hjnote 文件。\n\n{details}",
        "ignored_objects": "已忽略 {count} 项不支持或无法读取的内容",
        "about_title": "关于 Hinote2Jnotes",
        "about": "Hinote2Jnotes v{version}\n\n将华为笔记 Hinote 转换为云记 Jnotes。",
        "help_text": TRANSLATIONS[LANG_ZH]["help_text"].replace("Jnotes 文件", "华为笔记文件")
        + "\n\n支持 .hinote / .hjnote。无法转换的对象会跳过，并在 JSON 报告内统计。",
    },
    LANG_EN: {
        **TRANSLATIONS[LANG_EN],
        "title": "Hinote2Jnotes — Huawei Notes to Jnotes",
        "subtitle": "Convert Huawei Notes Hinote files to Jnotes notebooks",
        "output_file_error": "Batch output must be a directory, not a .Jnotes or .jnote file.",
        "nothing_found": "No .hinote or .hjnote files were found.\n\n{details}",
        "ignored_objects": "Skipped {count} unsupported or unreadable items",
        "about_title": "About Hinote2Jnotes",
        "about": "Hinote2Jnotes v{version}\n\nConvert Huawei Notes Hinote files to Jnotes notebooks.",
        "help_text": TRANSLATIONS[LANG_EN]["help_text"].replace("Jnotes files", "Huawei Notes files")
        + "\n\nSupports .hinote / .hjnote. Unsupported objects are skipped and counted in the JSON report.",
    },
}


class Hinote2JnotesApp(Jnotes2HinoteApp):
    app_name = APP_NAME
    translations = REVERSE_TRANSLATIONS
    input_suffixes = INPUT_SUFFIXES
    output_suffixes = OUTPUT_SUFFIXES
    file_pattern = "*.hinote *.hjnote"
    file_type_label: ClassVar[dict[str, str]] = {LANG_ZH: "华为笔记文件", LANG_EN: "Huawei Notes files"}
    collect_files = staticmethod(collect_input_files)
    run_batch = staticmethod(convert_batch)


def main() -> None:
    run_gui(Hinote2JnotesApp)


if __name__ == "__main__":
    main()
