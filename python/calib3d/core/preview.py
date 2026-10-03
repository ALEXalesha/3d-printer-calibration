"""Preview data: top and front views like preview() of the reference, in printer
coordinates. The windows draw them (Qt: ui/preview.py, web: js/ui/preview.js); this module
only picks the lines. Twin: web/js/core/preview.js."""

# Line colours by kind, as in the reference preview().
COLORS = {"top": "#fafafa", "wall": "#eb7828", "inner": "#c8aa3c", "infill": "#787878", "slab": "#5a8cdc",
          "bridge": "#285aff", "base": "#969696", "label": "#ff2828", "slow": "#3cb45a", "fast": "#e63ca0"}


def preview_data(res):
    g = res.g
    ctx = g.ctx
    ox, oy = ctx.ox, ctx.oy
    segs = [(s[0] + ox, s[1] + oy, s[2] + ox, s[3] + oy, s[4], s[5]) for s in g.segments]
    bed = ctx.p["bed"]
    out = {"bed": {"x": bed["x"], "y": bed["y"], "origin": bed["origin"], "shape": bed["shape"]},
           "top": [], "front": None, "max_z": res.max_z}
    if not segs:
        return out
    zmin = min(s[4] for s in segs)
    top_cut = zmin + ctx.H * 1.05
    out["top"] = [(s[0], s[1], s[2], s[3], s[5]) for s in segs if s[4] <= top_cut or s[5] == "label"]
    zmax = max(s[4] for s in segs)
    if zmax > 2 and any(s[4] > 1.0 for s in segs):
        body = [min(s[1], s[3]) for s in segs if s[5] != "label" and s[4] > 1.0]
        y_front = min(body)
        front = [(s[0], s[4], s[2], s[4], s[5]) for s in segs if min(s[1], s[3]) < y_front + 1.5 or s[5] == "label"]
        front.sort(key=lambda s: s[4] == "label")
        out["front"] = front
    return out


def layers(res):
    """All segments with their layer index, for the 3D view: (x1, y1, x2, y2, z, kind)."""
    g = res.g
    ox, oy = g.ctx.ox, g.ctx.oy
    return [(s[0] + ox, s[1] + oy, s[2] + ox, s[3] + oy, s[4], s[5]) for s in g.segments]
