"""python -m calib3d - the window.

    --self-test=<file>  no window: generate and check all tests for the reference profile,
                        build the window offscreen, write the result to <file>, exit 0/1.
"""
import multiprocessing
import os
import sys


def self_test(path):
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    lines, ok = [], True
    try:
        from calib3d.core import check, generator, profiles
        cc = profiles.printer("elegoo-centauri-carbon")
        for mid in ("petg", "pla"):
            for tid in generator.TEST_IDS:
                r = generator.generate(cc, profiles.material(mid), tid)
                problems = check.check_result(r, tid)
                ok = ok and not problems
                lines.append(f"{r.name}: {len(r.g.lines)} lines, {'ok' if not problems else problems}")
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance() or QApplication([])
        from calib3d.ui.app import MainWindow
        w = MainWindow(remember=False)
        lines.append(f"window: {w.windowTitle()}, version {profiles.version()}")
        w.gen.shutdown()
        del app
    except Exception as ex:  # report, do not crash silently
        ok = False
        lines.append(f"error: {type(ex).__name__}: {ex}")
    lines.append("SELF-TEST " + ("OK" if ok else "FAILED"))
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return 0 if ok else 1


if __name__ == "__main__":
    multiprocessing.freeze_support()     # the exe starts its generator worker through this
    for a in sys.argv[1:]:
        if a.startswith("--self-test="):
            sys.exit(self_test(a.split("=", 1)[1]))
    from calib3d.ui.app import main
    sys.exit(main())
