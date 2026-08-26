"""Mission-agnostic template-driven JSON generator.

Loads the placeholder Feature template (``feature_template.json``) and
deep-overlays value layers onto it, in order: mission-fixed map first, then
per-product dynamic values. No mission logic lives here — a mission plugs in
by passing its own layers, shaped as partial trees mirroring the template.
Overlay may add keys the template does not have, so a future mission can
carry extra fields without this module changing.

Merge rules (type-safe, see ``overlay``):
- dict + dict          -> recursive merge; keys new to the base are ADDED
- list + list of dicts -> element-wise merge by index (a partial dict fills
                          only the keys it carries); extra elements appended
- anything else        -> overlay value replaces the base value (numbers over
                          placeholder strings, coordinate arrays wholesale)

Validation: after merging, any string still containing a ``<...>`` placeholder
raises with the field path. Missions should ``prune`` their dynamic layer so a
missing extraction value leaves the placeholder in place (loud failure) rather
than writing null.
"""
import json
import re
from pathlib import Path

TEMPLATE_PATH = Path(__file__).resolve().parent / "feature_template.json"

_PLACEHOLDER = re.compile(r"<[^<>]*>")


def load_template(template_path=TEMPLATE_PATH):
    with open(template_path, "r", encoding="utf-8") as fd:
        return json.load(fd)


def overlay(base, over):
    if isinstance(base, dict) and isinstance(over, dict):
        merged = dict(base)
        for key, value in over.items():
            merged[key] = overlay(base[key], value) if key in base else value
        return merged
    if (isinstance(base, list) and isinstance(over, list)
            and all(isinstance(e, dict) for e in base + over)):
        merged = [overlay(b, o) for b, o in zip(base, over)]
        longer = base if len(base) > len(over) else over
        merged.extend(longer[len(merged):])
        return merged
    if isinstance(base, list) and isinstance(over, dict) and base:
        return [overlay(base[0], over)] + base[1:]
    return over


def prune(layer):
    """Drop None values and branches that become empty, so a missing value
    leaves the template placeholder in place and fails validation with the
    field path instead of silently writing null."""
    if isinstance(layer, dict):
        pruned = {k: prune(v) for k, v in layer.items() if v is not None}
        return {k: v for k, v in pruned.items() if v not in ({}, [])}
    if isinstance(layer, list):
        return [prune(v) for v in layer if v is not None]
    return layer


def find_placeholders(node, path="$"):
    found = []
    if isinstance(node, dict):
        for key, value in node.items():
            found.extend(find_placeholders(value, "%s.%s" % (path, key)))
    elif isinstance(node, list):
        for i, value in enumerate(node):
            found.extend(find_placeholders(value, "%s[%d]" % (path, i)))
    elif isinstance(node, str) and _PLACEHOLDER.search(node):
        found.append((path, node))
    return found


def lineage_citation(feature):
    """Return the native citation from either supported lineage shape."""
    lineage = feature["properties"]["productInformation"]["resourceLineage"]
    process_step = lineage[0]["processStep"][0] if isinstance(lineage, list) else lineage["processStep"]
    source = process_step["source"]
    return source[0]["citation"] if isinstance(source, list) else source["citation"]


def build(*layers, template_path=TEMPLATE_PATH):
    feature = load_template(template_path)
    for layer in layers:
        feature = overlay(feature, layer)
    return feature


def validate(feature):
    leftovers = find_placeholders(feature)
    if leftovers:
        raise ValueError("unfilled template placeholders: %s"
                         % "; ".join("%s = %s" % (p, v) for p, v in leftovers))
    return True


def write_json(feature, out_dir, eo_product_name):
    out_path = Path(out_dir) / ("%s.JSON" % eo_product_name)
    with open(out_path, "w", encoding="utf-8") as fd:
        json.dump(feature, fd, indent=2, ensure_ascii=False)
    return str(out_path)


def emit(out_dir, eo_product_name, *layers, template_path=TEMPLATE_PATH,
         do_validate=True):
    feature = build(*layers, template_path=template_path)
    if do_validate:
        validate(feature)
    return write_json(feature, out_dir, eo_product_name)
