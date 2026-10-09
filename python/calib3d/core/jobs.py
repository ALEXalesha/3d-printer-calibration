"""One test, generated and checked, as plain data - for a worker process.

The window used to generate in a thread. Generation is pure Python (about 4 s of CPU for
all ten tests on the reference profile), and a Python thread shares the interpreter lock
with the window: while it ran, every repaint and click waited for its turn (stalls of up
to 750 ms measured offscreen, tools/profile_ui.py). A separate process has its own lock,
so the window stays free. Nothing here imports Qt.
"""
from . import check, generator, params, preview


def run_job(printer, material, test_id, prm, lang):
    try:
        res = generator.generate(printer, material, test_id, prm, lang)
    except generator.DoesNotFit:
        return {"ok": False, "error": "does_not_fit"}
    except Exception as ex:  # a bad profile must not crash the window
        return {"ok": False, "error": str(ex)}
    return {"ok": True, "summary": params.summary(res), "problems": check.check_result(res, test_id),
            "preview": preview.preview_data(res), "text": res.text}
