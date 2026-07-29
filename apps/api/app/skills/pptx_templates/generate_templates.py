"""Generate styled PPTX template files for course slide decks.

Modifies layout XML directly to set backgrounds and placeholder styling.
Styles layouts 0 (Title), 1 (Content), and 5 (TwoColumn).

Run:
    cd apps/api && python -m app.skills.pptx_templates.generate_templates
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from lxml import etree

from pptx import Presentation
from pptx.util import Inches

TEMPLATE_DIR = Path(__file__).parent

NSMAP = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}

THEMES: dict[str, dict[str, Any]] = {
    "academic_blue": {
        "name": "学术蓝",
        "cover_bg": "1A3A5C",
        "accent": "4A90D9",
        "cover_title": "FFFFFF",
        "cover_sub": "B0C4DE",
        "body_bg": "F5F8FC",
        "title_clr": "1A3A5C",
        "text_clr": "2C3E50",
        "divider": "4A90D9",
    },
    "vibrant_green": {
        "name": "活力绿",
        "cover_bg": "1B5E20",
        "accent": "4CAF50",
        "cover_title": "FFFFFF",
        "cover_sub": "C8E6C9",
        "body_bg": "F1F8E9",
        "title_clr": "1B5E20",
        "text_clr": "33691E",
        "divider": "4CAF50",
    },
    "warm_orange": {
        "name": "温暖橙",
        "cover_bg": "BF360C",
        "accent": "FF7043",
        "cover_title": "FFFFFF",
        "cover_sub": "FFCCBC",
        "body_bg": "FFF8E1",
        "title_clr": "BF360C",
        "text_clr": "4E342E",
        "divider": "FF7043",
    },
    "tech_purple": {
        "name": "科技紫",
        "cover_bg": "4A148C",
        "accent": "AB47BC",
        "cover_title": "FFFFFF",
        "cover_sub": "D1C4E9",
        "body_bg": "F3E5F5",
        "title_clr": "4A148C",
        "text_clr": "311B92",
        "divider": "AB47BC",
    },
}


def _solid_fill_xml(color_hex: str) -> str:
    return (
        f'<p:bg xmlns:p="{NSMAP["p"]}" xmlns:a="{NSMAP["a"]}">'
        f"  <p:bgPr>"
        f'    <a:solidFill><a:srgbClr val="{color_hex}"/></a:solidFill>'
        f"    <a:effectLst/>"
        f"  </p:bgPr>"
        f"</p:bg>"
    )


def _set_layout_bg(layout, color_hex: str) -> None:
    """Set the background color of a slide layout via XML."""
    bg_xml = _solid_fill_xml(color_hex)
    bg_elem = etree.fromstring(bg_xml)
    # Remove existing bg element if present
    existing = layout._element.find(f'{{{NSMAP["p"]}}}bg')
    if existing is not None:
        layout._element.remove(existing)
    # Insert bg before cSld
    cSld = layout._element.find(f'{{{NSMAP["p"]}}}cSld')
    if cSld is not None:
        layout._element.insert(list(layout._element).index(cSld), bg_elem)


def _add_accent_bar_xml(layout, color_hex: str) -> None:
    """Add a left accent bar shape to a layout via XML."""
    cSld = layout._element.find(f'{{{NSMAP["p"]}}}cSld')
    if cSld is None:
        return
    spTree = cSld.find(f'{{{NSMAP["p"]}}}spTree')
    if spTree is None:
        return

    # EMU values: left=0, top=0, width=137160 (0.15in), height=6858000 (7.5in)
    shape_xml = (
        f'<p:sp xmlns:p="{NSMAP["p"]}" xmlns:a="{NSMAP["a"]}">'
        f"  <p:nvSpPr>"
        f'    <p:cNvPr id="99" name="AccentBar"/>'
        f"    <p:cNvSpPr/>"
        f'    <p:nvPr/>'
        f"  </p:nvSpPr>"
        f"  <p:spPr>"
        f'    <a:xfrm><a:off x="0" y="0"/><a:ext cx="114300" cy="6858000"/></a:xfrm>'
        f"    <a:prstGeom prst=\"rect\"><a:avLst/></a:prstGeom>"
        f'    <a:solidFill><a:srgbClr val="{color_hex}"/></a:solidFill>'
        f"    <a:ln><a:noFill/></a:ln>"
        f"  </p:spPr>"
        f"  <p:txBody>"
        f"    <a:bodyPr/>"
        f"    <a:p><a:endParaRPr/></a:p>"
        f"  </p:txBody>"
        f"</p:sp>"
    )
    shape_elem = etree.fromstring(shape_xml)
    spTree.append(shape_elem)


def _add_divider_xml(layout, color_hex: str) -> None:
    """Add a thin horizontal divider line below the title area."""
    cSld = layout._element.find(f'{{{NSMAP["p"]}}}cSld')
    if cSld is None:
        return
    spTree = cSld.find(f'{{{NSMAP["p"]}}}spTree')
    if spTree is None:
        return

    # x=457200(0.5in), y=1097280(1.2in), width=1645920(1.8in), height=23876(~0.026in)
    shape_xml = (
        f'<p:sp xmlns:p="{NSMAP["p"]}" xmlns:a="{NSMAP["a"]}">'
        f"  <p:nvSpPr>"
        f'    <p:cNvPr id="98" name="Divider"/>'
        f"    <p:cNvSpPr/>"
        f'    <p:nvPr/>'
        f"  </p:nvSpPr>"
        f"  <p:spPr>"
        f'    <a:xfrm><a:off x="457200" y="1097280"/><a:ext cx="1645920" cy="23876"/></a:xfrm>'
        f"    <a:prstGeom prst=\"rect\"><a:avLst/></a:prstGeom>"
        f'    <a:solidFill><a:srgbClr val="{color_hex}"/></a:solidFill>'
        f"    <a:ln><a:noFill/></a:ln>"
        f"  </p:spPr>"
        f"  <p:txBody>"
        f"    <a:bodyPr/>"
        f"    <a:p><a:endParaRPr/></a:p>"
        f"  </p:txBody>"
        f"</p:sp>"
    )
    shape_elem = etree.fromstring(shape_xml)
    spTree.append(shape_elem)


def generate_template(theme_key: str, theme: dict[str, Any]) -> Path:
    prs = Presentation()
    prs.slide_width = Inches(10)
    prs.slide_height = Inches(7.5)

    # Layout 0: Title Slide — full-color cover
    _set_layout_bg(prs.slide_layouts[0], theme["cover_bg"])

    # Layout 1: Title + Content — light bg + accent bar + divider
    _set_layout_bg(prs.slide_layouts[1], theme["body_bg"])
    _add_accent_bar_xml(prs.slide_layouts[1], theme["accent"])
    _add_divider_xml(prs.slide_layouts[1], theme["divider"])

    # Layout 5: Two Content (if available)
    if len(prs.slide_layouts) > 5:
        _set_layout_bg(prs.slide_layouts[5], theme["body_bg"])
        _add_accent_bar_xml(prs.slide_layouts[5], theme["accent"])
        _add_divider_xml(prs.slide_layouts[5], theme["divider"])

    output = TEMPLATE_DIR / f"{theme_key}.pptx"
    prs.save(output)
    print(f"  OK {theme['name']} -> {output.name}")
    return output


def main() -> None:
    print("Generating PPTX templates...")
    for key, theme in THEMES.items():
        generate_template(key, theme)
    print(f"\nDone! {len(THEMES)} templates in {TEMPLATE_DIR}")


if __name__ == "__main__":
    main()
