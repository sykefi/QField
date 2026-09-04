#!/usr/bin/env python3
"""Convert a simple SVG (nested <g> with translate/matrix transforms, <path>,
<polygon>, flat fills) into an Android VectorDrawable.

Only what the SYKE logo needs is supported; anything else raises.
Usage: svg_to_vector.py in.svg out.xml
"""
import re
import sys
import xml.etree.ElementTree as ET

NS = "{http://www.w3.org/2000/svg}"


def parse_transform(t):
    """Return (sx, sy, tx, ty) for translate()/matrix() with no skew/rotation."""
    if not t:
        return None
    m = re.fullmatch(r"\s*translate\(\s*([-\d.eE]+)[,\s]+([-\d.eE]+)\s*\)\s*", t)
    if m:
        return 1.0, 1.0, float(m.group(1)), float(m.group(2))
    m = re.fullmatch(r"\s*matrix\(\s*([-\d.eE]+)[,\s]+([-\d.eE]+)[,\s]+([-\d.eE]+)[,\s]+([-\d.eE]+)[,\s]+([-\d.eE]+)[,\s]+([-\d.eE]+)\s*\)\s*", t)
    if m:
        a, b, c, d, e, f = map(float, m.groups())
        if b != 0 or c != 0:
            raise SystemExit(f"unsupported transform with skew/rotation: {t}")
        return a, d, e, f
    raise SystemExit(f"unsupported transform: {t}")


def style_dict(s):
    return dict(kv.split(":", 1) for kv in s.split(";") if ":" in kv) if s else {}


def resolve_fill(el, classes):
    st = style_dict(el.get("style", ""))
    fill = st.get("fill") or el.get("fill")
    if not fill:
        for cls in el.get("class", "").split():
            fill = classes.get(cls, {}).get("fill", fill)
    if not fill or fill == "none":
        return None
    return fill.strip().upper()


def polygon_to_path(points):
    nums = [float(x) for x in re.split(r"[\s,]+", points.strip()) if x]
    pts = list(zip(nums[::2], nums[1::2]))
    return "M" + " L".join(f"{x:g},{y:g}" for x, y in pts) + " Z"


def emit(el, classes, out, depth):
    ind = "    " * depth
    tag = el.tag.replace(NS, "")
    if tag == "g":
        tr = parse_transform(el.get("transform"))
        attrs = [f'android:name="{el.get("id", "")}"'] if el.get("id") else []
        if tr:
            sx, sy, tx, ty = tr
            attrs += [f'android:scaleX="{sx:g}"', f'android:scaleY="{sy:g}"',
                      f'android:translateX="{tx:g}"', f'android:translateY="{ty:g}"']
        children = [c for c in el if c.tag.replace(NS, "") in ("g", "path", "polygon")]
        if not children:
            return
        out.append(f"{ind}<group " + " ".join(attrs) + ">")
        for c in children:
            emit(c, classes, out, depth + 1)
        out.append(f"{ind}</group>")
    elif tag in ("path", "polygon"):
        if el.get("transform"):
            raise SystemExit("transform on a path is unsupported; wrap it in a <g>")
        d = el.get("d") if tag == "path" else polygon_to_path(el.get("points"))
        d = re.sub(r"\s+", " ", d.strip())
        fill = resolve_fill(el, classes)
        if fill is None:
            return
        out.append(f'{ind}<path android:name="{el.get("id", "")}" android:fillColor="{fill}"')
        out.append(f'{ind}    android:pathData="{d}"/>')


def main(src, dst):
    root = ET.parse(src).getroot()
    vb = [float(v) for v in root.get("viewBox").split()]
    if vb[:2] != [0.0, 0.0]:
        raise SystemExit("viewBox must start at 0 0")
    classes = {}
    for style in root.iter(NS + "style"):
        for m in re.finditer(r"\.([\w-]+)\s*\{([^}]*)\}", style.text or ""):
            classes[m.group(1)] = style_dict(m.group(2))
    out = ['<vector xmlns:android="http://schemas.android.com/apk/res/android"',
           f'    android:viewportWidth="{vb[2]:g}"',
           f'    android:viewportHeight="{vb[3]:g}"',
           f'    android:width="{vb[2]:g}dp"',
           f'    android:height="{vb[3]:g}dp">']
    for c in root:
        if c.tag.replace(NS, "") in ("g", "path", "polygon"):
            emit(c, classes, out, 1)
    out.append("</vector>")
    with open(dst, "w") as f:
        f.write("\n".join(out) + "\n")
    print(f"wrote {dst}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
