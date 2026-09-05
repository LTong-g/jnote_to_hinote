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


def _run_runtime_self_test() -> int:
    try:
        import pypdf  # noqa: F401
        import pypdfium2  # noqa: F401
        import pypdfium2_raw  # noqa: F401

        from jnotes2hinote.gui import create_root

        root = create_root()
        root.withdraw()
        root.update_idletasks()
        root.destroy()
    except Exception:  # noqa: BLE001 - self-test must report every frozen-runtime failure
        log_path = os.environ.get("JNOTES2HINOTE_SELF_TEST_LOG")
        if log_path:
            import traceback

            with open(log_path, "w", encoding="utf-8") as log:
                log.write(traceback.format_exc())
        return 86
    return 0


if __name__ == "__main__":
    if "--self-test-runtime" in sys.argv[1:]:
        raise SystemExit(_run_runtime_self_test())
    from jnotes2hinote.gui import main

    main()
