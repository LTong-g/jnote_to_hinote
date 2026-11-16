"""Use the shared batch workflow with Huawei input and Jnotes output."""

from functools import partial

from jnotes2hinote import batch

from .converter import convert
from .writer import OUTPUT_SUFFIX

INPUT_SUFFIXES = {".hinote", ".hjnote"}

collect_input_files = partial(batch.collect_input_files, suffixes=INPUT_SUFFIXES, format_name="华为笔记")
convert_batch = partial(batch.convert_batch, converter=convert, output_suffix=OUTPUT_SUFFIX)
