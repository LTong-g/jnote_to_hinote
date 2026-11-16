import sys

from gui_entry import _run_runtime_self_test

from hinote2jnotes.gui import Hinote2JnotesApp, main

if __name__ == "__main__":
    if "--self-test-runtime" in sys.argv[1:]:
        raise SystemExit(_run_runtime_self_test(Hinote2JnotesApp))
    main()
