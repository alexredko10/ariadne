"""Whitelist-based SVG sanitizer.

Produces a static, inert SVG document safe for innerHTML insertion.
Uses xml.etree.ElementTree for parsing and whitelist-based traversal.

Removals (unconditional):
- script, foreignObject, iframe, embed, object, img, image, use
- feImage, animate, animateTransform, animateMotion, set, discard
- Event handler attributes: on* (onclick, onerror, onload, onmouseover, ...)
- href, xlink:href, target
- style attribute (inline CSS)
- a (anchor) elements
- External references: feImage, img src
- Unknown elements and unknown attributes

Allowed elements and their attributes:
    See _ALLOWED_ELEMENTS and _ALLOWED_ATTRS constants.

If parsing fails, returns ok=False with error="svg_parse_error".
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

# ---------------------------------------------------------------------------
# Whitelist definitions
# ---------------------------------------------------------------------------

_ALLOWED_ELEMENTS: set[str] = {
    "svg",
    "g",
    "path",
    "rect",
    "circle",
    "ellipse",
    "line",
    "polyline",
    "polygon",
    "text",
    "tspan",
    "defs",
    "linearGradient",
    "radialGradient",
    "stop",
    "marker",
    "clipPath",
    "mask",
    "pattern",
    "title",
    "desc",
}

# Standard SVG presentation attributes only
_ALLOWED_ATTRS: set[str] = {
    "id",
    "class",
    # Coordinates
    "x",
    "y",
    "x1",
    "y1",
    "x2",
    "y2",
    "cx",
    "cy",
    "r",
    "rx",
    "ry",
    "width",
    "height",
    "d",
    "points",
    # Transform and layout
    "transform",
    "viewBox",
    "preserveAspectRatio",
    "xmlns",
    # Presentation
    "fill",
    "stroke",
    "stroke-width",
    "stroke-linecap",
    "stroke-linejoin",
    "stroke-dasharray",
    "stroke-dashoffset",
    "opacity",
    "fill-opacity",
    "stroke-opacity",
    # Text
    "font-family",
    "font-size",
    "font-weight",
    "font-style",
    "text-anchor",
    "dominant-baseline",
    "text-decoration",
    "letter-spacing",
    # Gradients
    "stop-color",
    "stop-opacity",
    "offset",
    "gradientUnits",
    "gradientTransform",
    "spreadMethod",
    # Markers
    "markerWidth",
    "markerHeight",
    "markerUnits",
    "orient",
    "refX",
    "refY",
    # Clip and mask
    "clip-path",
    "clip-rule",
    "fill-rule",
    "maskUnits",
    "maskContentUnits",
    "patternUnits",
    "patternTransform",
    "patternContentUnits",
    # Version / metadata
    "version",
}

# Namespace URI for SVG
_SVG_NS = "http://www.w3.org/2000/svg"


# ---------------------------------------------------------------------------
# Core sanitizer
# ---------------------------------------------------------------------------


def sanitize_svg(svg_string: str) -> dict[str, Any]:
    """Sanitize an SVG string via whitelist-based traversal.

    Parameters
    ----------
    svg_string:
        Raw SVG string to sanitize.

    Returns
    -------
    dict with keys:
        ok (bool) — True if sanitization succeeded.
        sanitized_svg (str|None) — Sanitized SVG string on success.
        error (str|None) — Error code on failure.
    """
    if not svg_string or not svg_string.strip():
        return {"ok": False, "sanitized_svg": None, "error": "empty_input"}

    try:
        root = ET.fromstring(svg_string)
    except ET.ParseError:
        return {"ok": False, "sanitized_svg": None, "error": "svg_parse_error"}
    except Exception:
        return {"ok": False, "sanitized_svg": None, "error": "svg_parse_error"}

    # Build namespace map from the original to preserve xmlns declarations
    ns_map = _collect_namespaces(root)
    # Include svg namespace if not already present
    if "" not in ns_map:
        ns_map[""] = _SVG_NS

    _sanitize_element(root)

    try:
        # Register namespaces before serialization
        for prefix, uri in ns_map.items():
            ET.register_namespace(prefix, uri)
        sanitized = _serialize_svg(root)
    except Exception:
        return {"ok": False, "sanitized_svg": None, "error": "svg_serialization_error"}

    return {"ok": True, "sanitized_svg": sanitized, "error": None}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _collect_namespaces(root: ET.Element) -> dict[str, str]:
    """Collect all namespace declarations from the root element."""
    ns_map: dict[str, str] = {}
    # Default namespace
    default_ns = root.tag.split("}")[0].lstrip("{") if "}" in root.tag else ""
    if default_ns:
        ns_map[""] = default_ns
    # Explicit xmlns:* attributes
    for key, value in root.attrib.items():
        if key.startswith("xmlns:"):
            prefix = key[len("xmlns:"):]
            ns_map[prefix] = value
        elif key == "xmlns":
            ns_map[""] = value
    return ns_map


def _is_event_handler(attr_name: str) -> bool:
    """Return True if attr_name is an event handler (starts with 'on')."""
    return attr_name.lower().startswith("on")


def _is_dangerous_attr(attr_name: str) -> bool:
    """Return True if attr_name is forbidden regardless of element.
    
    Includes: event handlers, href-related, style, target.
    """
    lower = attr_name.lower()
    if _is_event_handler(lower):
        return True
    if lower in {"href", "xlink:href", "target", "style"}:
        return True
    return False


def _sanitize_element(element: ET.Element) -> None:
    """Sanitize an XML element in-place using iterative post-order traversal.

    First collects all element nodes in post-order (children before parent),
    then processes each node: removes disallowed elements from their parent,
    and strips dangerous attributes from allowed elements.
    """
    # Collect all element nodes in post-order traversal
    post_order: list[ET.Element] = []
    stack = [element]
    while stack:
        current = stack.pop()
        # Prepend to get post-order after reversal
        post_order.append(current)
        for child in reversed(list(current)):
            if isinstance(child.tag, str):
                stack.append(child)
    # Reverse to get post-order (children before parents)
    post_order.reverse()

    # Build parent map once
    parent_map: dict[ET.Element, ET.Element | None] = {}
    _build_parent_map(element, parent_map)

    for node in post_order:
        # Strip namespace from tag for whitelist matching
        tag = node.tag
        if "}" in tag:
            tag = tag.split("}", 1)[1]

        if tag not in _ALLOWED_ELEMENTS:
            parent = parent_map.get(node)
            if parent is not None:
                parent.remove(node)
            continue

        # Sanitize attributes on allowed elements
        attrs_to_remove: list[str] = []
        for attr_name in node.attrib:
            if _is_dangerous_attr(attr_name):
                attrs_to_remove.append(attr_name)
                continue
            # Strip namespace for attribute matching
            local_attr = attr_name
            if "}" in local_attr:
                local_attr = local_attr.split("}", 1)[1]
            if local_attr not in _ALLOWED_ATTRS:
                attrs_to_remove.append(attr_name)

        for attr_name in attrs_to_remove:
            del node.attrib[attr_name]


def _build_parent_map(
    element: ET.Element,
    parent_map: dict[ET.Element, ET.Element | None],
    parent: ET.Element | None = None,
) -> None:
    """Populate parent_map by traversing element tree."""
    parent_map[element] = parent
    for child in element:
        if isinstance(child.tag, str):
            _build_parent_map(child, parent_map, element)


def _serialize_svg(root: ET.Element) -> str:
    """Serialize an ElementTree root back to an SVG string.

    Uses xml.etree.ElementTree.tostring with XML declaration.
    """
    raw = ET.tostring(root, encoding="unicode", method="xml")
    # Ensure XML declaration is present
    if not raw.startswith("<?xml"):
        raw = '<?xml version="1.0" encoding="UTF-8"?>\n' + raw
    return raw
