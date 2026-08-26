import os
import sys


def _configure_frozen_tk() -> None:
    """Use the explicit Tcl/Tk data directories bundled by the build."""
    meipass = getattr(sys, "_MEIPASS", None)
    if not meipass:
        return
    tcl_dir = os.path.join(meipass, "_tcl_data")
    tk_dir = os.path.join(meipass, "_tk_data")
    if os.path.isdir(tcl_dir):
        os.environ["TCL_LIBRARY"] = tcl_dir
    if os.path.isdir(tk_dir):
        os.environ["TK_LIBRARY"] = tk_dir


_configure_frozen_tk()

from jnotes2hinote.gui import main


if __name__ == "__main__":
    main()
