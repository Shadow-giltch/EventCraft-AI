"""Static accessibility and WCAG 2.2 AA compliance test suite."""

import re
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

STATIC_DIR = Path(__file__).resolve().parent.parent.parent / "src" / "eventcraft" / "static"
HTML_PATH = STATIC_DIR / "index.html"
CSS_PATH = STATIC_DIR / "css" / "style.css"


def _luminance(r: int, g: int, b: int) -> float:
    """Calculate relative luminance for an sRGB color."""
    vals: list[float] = []
    for c in (r, g, b):
        sc = c / 255.0
        if sc <= 0.03928:
            vals.append(sc / 12.92)
        else:
            vals.append(((sc + 0.055) / 1.055) ** 2.4)
    return 0.2126 * vals[0] + 0.7152 * vals[1] + 0.0722 * vals[2]


def _contrast_ratio(hex1: str, hex2: str) -> float:
    """Compute WCAG contrast ratio between two hex colors."""
    h1 = hex1.lstrip("#")
    h2 = hex2.lstrip("#")
    r1, g1, b1 = int(h1[0:2], 16), int(h1[2:4], 16), int(h1[4:6], 16)
    r2, g2, b2 = int(h2[0:2], 16), int(h2[2:4], 16), int(h2[4:6], 16)
    lum1 = _luminance(r1, g1, b1)
    lum2 = _luminance(r2, g2, b2)
    brightest = max(lum1, lum2)
    darkest = min(lum1, lum2)
    return (brightest + 0.05) / (darkest + 0.05)


@pytest.fixture
def html_soup() -> BeautifulSoup:
    """Load and parse static index.html with BeautifulSoup."""
    assert HTML_PATH.exists(), f"Missing index.html at {HTML_PATH}"
    content = HTML_PATH.read_text(encoding="utf-8")
    return BeautifulSoup(content, "html.parser")


def test_html_lang_attribute(html_soup: BeautifulSoup) -> None:
    """HTML tag must specify a valid language code."""
    html_tag = html_soup.find("html")
    assert html_tag is not None
    assert html_tag.get("lang") == "en"


def test_single_h1_heading(html_soup: BeautifulSoup) -> None:
    """Document must have exactly one top-level h1 heading."""
    h1_tags = html_soup.find_all("h1")
    assert len(h1_tags) == 1
    assert "EventCraft AI" in h1_tags[0].get_text()


def test_required_landmarks_present(html_soup: BeautifulSoup) -> None:
    """Document must contain standard accessible landmark regions."""
    assert html_soup.find("header") is not None
    assert html_soup.find("main") is not None
    assert html_soup.find("footer") is not None
    assert len(html_soup.find_all("nav")) >= 1


def test_skip_link_present_and_targets_main(html_soup: BeautifulSoup) -> None:
    """Skip link must be early in body and point to the main content container."""
    skip_link = html_soup.find("a", class_="skip-link")
    assert skip_link is not None
    assert skip_link.get("href") == "#main-content"

    main_tag = html_soup.find("main", id="main-content")
    assert main_tag is not None


def test_all_form_controls_have_associated_labels(html_soup: BeautifulSoup) -> None:
    """Every form input, select, and textarea must have a matching label."""
    form = html_soup.find("form", id="brief-form")
    assert form is not None

    controls = form.find_all(["input", "select", "textarea"])
    for control in controls:
        ctrl_id = control.get("id")
        assert ctrl_id, f"Control missing id attribute: {control}"
        label = html_soup.find("label", attrs={"for": ctrl_id})
        assert label is not None, f"Missing label for control #{ctrl_id}"
        assert label.get_text().strip(), f"Empty label text for #{ctrl_id}"


def test_no_positive_tabindex(html_soup: BeautifulSoup) -> None:
    """Positive tabindex violates natural tab order; only 0 or -1 are allowed."""
    for element in html_soup.find_all(True):
        if element.has_attr("tabindex"):
            tabindex_val = int(str(element["tabindex"]))
            assert tabindex_val <= 0, f"Illegal positive tabindex ({tabindex_val}) on {element}"


def test_no_inline_scripts_or_event_handlers(html_soup: BeautifulSoup) -> None:
    """Strict security and accessibility: no inline onclick or inline scripts."""
    for tag in html_soup.find_all():
        for attr in tag.attrs:
            assert not attr.startswith("on"), f"Forbidden inline event handler '{attr}' on {tag}"
        assert "style" not in tag.attrs, f"Forbidden inline style attribute on {tag}"

    script_tags = html_soup.find_all("script")
    for script in script_tags:
        assert script.get("src") is not None, "Inline script tags are forbidden"


def test_css_wcag_contrast_ratios() -> None:
    """Ensure color palette variables satisfy WCAG 2.2 AA contrast >= 4.5:1."""
    assert CSS_PATH.exists()
    css_content = CSS_PATH.read_text(encoding="utf-8")

    def get_var(name: str) -> str:
        match = re.search(rf"{name}:\s*(#[0-9a-fA-F]{{6}})", css_content)
        assert match, f"Missing CSS color variable {name}"
        return match.group(1)

    # Light mode checks
    bg = get_var("--color-bg")
    surface = get_var("--color-surface")
    text = get_var("--color-text")
    primary = get_var("--color-primary")

    contrast_text_bg = _contrast_ratio(text, bg)
    contrast_text_surface = _contrast_ratio(text, surface)
    contrast_primary_white = _contrast_ratio(primary, "#ffffff")

    assert contrast_text_bg >= 4.5, f"Text on bg contrast too low: {contrast_text_bg}"
    assert contrast_text_surface >= 4.5, (
        f"Text on surface contrast too low: {contrast_text_surface}"
    )
    assert contrast_primary_white >= 4.5, (
        f"Primary button contrast too low: {contrast_primary_white}"
    )
