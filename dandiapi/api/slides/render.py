"""Render a CC-0 shareable slide for a published Dandiset Version as SVG.

Produces a 1920x1080 SVG document summarizing a Version (title, DOI, contributors,
key stats, citation, QR code) so researchers can drop it into talks. PNG
rasterization is left to the caller (e.g. librsvg / rsvg-convert at the email
or storage layer).

Not yet wired into the publish flow; see issue #2797.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
import re
from typing import TYPE_CHECKING
from xml.sax.saxutils import escape

import qrcode
from qrcode.image.svg import SvgPathImage

if TYPE_CHECKING:
    from dandiapi.api.models import Version

# --- Layout ------------------------------------------------------------------
W = 1920
H = 1080

# --- Brand palette (from web/src/assets/logo.svg + Vuetify theme) -----------
NAVY = '#00436D'
CORAL = '#D3868D'
INK = '#1a1a1a'
MUTED = '#5b6b7d'
BG = '#ffffff'
PANEL = '#f4f7fa'

# --- Logo asset (verbatim copy of web/src/assets/logo.svg) ------------------
_LOGO_PATH = Path(__file__).parent / 'dandi_logo.svg'

# Map the source <style>.stN{fill:...}</style> classes to direct fill attrs so
# the logo renders correctly when embedded as an <image> data URI (rsvg-convert
# does not apply CSS rules across image boundaries).
_LOGO_FILL_BY_CLASS = {
    'st0': '#D3868D',
    'st1': '#F0A5AC',
    'st2': '#A05A60',
    'st3': '#FFFFFF',
    'st4': '#00436D',
}


def _inline_logo_fills(svg_text: str) -> str:
    out = svg_text
    for cls, color in _LOGO_FILL_BY_CLASS.items():
        out = re.sub(rf'class="{cls}"', f'fill="{color}"', out)
    return re.sub(r'<style[^>]*>.*?</style>', '', out, flags=re.DOTALL)


_LOGO_SVG_INLINED = _inline_logo_fills(_LOGO_PATH.read_text(encoding='utf-8'))

# Extract the inner content of the logo <svg> so it can be nested as a child
# <svg> element in the composed slide (cleaner than data-URI encoding).
_LOGO_INNER_MATCH = re.search(r'<svg[^>]*>(.*)</svg>', _LOGO_SVG_INLINED, re.DOTALL)
_LOGO_SVG_INLINED_INNER = _LOGO_INNER_MATCH.group(1) if _LOGO_INNER_MATCH else ''


# --- Formatting helpers ------------------------------------------------------
_MODALITY_LABELS = {
    'electrophysiological approach': 'Ecephys',
    'behavioral approach': 'Behavior',
    'optical physiology approach': 'Ophys',
    'imaging approach': 'Imaging',
}


def _fmt_size(n: int) -> str:
    """SI base-10 formatting to match the Dandiset Landing Page convention."""
    value = float(n)
    for unit in ('B', 'kB', 'MB', 'GB', 'TB', 'PB'):
        if value < 1000:
            return f'{value:.1f} {unit}'
        value /= 1000
    return f'{value:.1f} EB'


def _fmt_count(n: int) -> str:
    if n >= 1_000_000:
        return f'{n / 1_000_000:.1f}M'
    if n >= 1_000:
        return f'{n / 1_000:.1f}k'
    return str(n)


def _reformat_person(name: str) -> str:
    """Convert DANDI's "Last, First Middle" name format to "F. Last"."""
    if ',' not in name:
        return name
    last, first = (s.strip() for s in name.split(',', 1))
    initials = ''.join(f'{part[0]}.' for part in first.split() if part)
    return f'{initials} {last}'.strip() if initials else last


def _strip_prefix(s: str, prefix: str) -> str:
    return s.removeprefix(prefix)


def _truncate_at_word(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(' ', 1)[0] + '…'


def _wrap(text: str, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur = ''
    for w in words:
        trial = (cur + ' ' + w).strip()
        if len(trial) > width:
            lines.append(cur)
            cur = w
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


def _truncate_contributors(names: list[str], max_chars: int) -> str:
    """Join names up to a character budget, appending "+N more" overflow."""
    shown: list[str] = []
    running = 0
    overflow_reserve = 12  # room for a trailing "+NN more"
    for n in names:
        add = (2 if shown else 0) + len(n)
        if running + add > max_chars - overflow_reserve:
            break
        shown.append(n)
        running += add
    line = ', '.join(shown)
    remaining = len(names) - len(shown)
    if remaining > 0:
        line += f', +{remaining} more'
    return line


def _qr_svg(url: str, size: int) -> str:
    """Render a QR code as an SVG <g> snippet sized to fit `size` x `size`."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=0,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(image_factory=SvgPathImage, fill_color=NAVY)
    buf = BytesIO()
    img.save(buf)
    inner = buf.getvalue().decode('utf-8')
    # SvgPathImage emits a full <svg> element with its own width/height.
    # Inline only the path so we can position and scale it ourselves.
    match = re.search(r'<svg[^>]*viewBox="([^"]+)"[^>]*>(.*)</svg>', inner, re.DOTALL)
    if not match:
        return ''
    view_box, body = match.group(1), match.group(2)
    return (
        f'<svg x="0" y="0" width="{size}" height="{size}" viewBox="{view_box}" '
        f'preserveAspectRatio="xMidYMid meet">{body}</svg>'
    )


# --- Metadata extraction -----------------------------------------------------
def _extract_data(version: Version) -> dict:
    """Pull the fields the slide needs out of a Version's metadata payload."""
    metadata: dict = version.metadata or {}
    summary: dict = metadata.get('assetsSummary') or {}

    cited = [c for c in metadata.get('contributor', []) if c.get('includeInCitation')]
    orgs = [c['name'] for c in cited if c.get('schemaKey') == 'Organization']
    persons = [_reformat_person(c['name']) for c in cited if c.get('schemaKey') == 'Person']
    contributors = orgs + persons

    modalities = [
        _MODALITY_LABELS.get(a.get('name', ''), a.get('name', ''))
        for a in summary.get('approach', [])
    ]
    standards = [
        s.get('name', '').replace('Neurodata Without Borders (NWB)', 'NWB')
        for s in summary.get('dataStandard', [])
    ]
    species = [s.get('name', '').split(' - ')[0] for s in summary.get('species', [])]

    licenses = [_strip_prefix(lic, 'spdx:') for lic in metadata.get('license', [])]
    published = (metadata.get('datePublished') or '')[:10]

    return {
        'identifier': version.dandiset.identifier,
        'version': version.version,
        'title': metadata.get('name') or version.name or '',
        'doi': metadata.get('doi') or version.doi or '',
        'description': metadata.get('description') or '',
        'contributors': contributors,
        'file_count': summary.get('numberOfFiles', 0),
        'size_bytes': summary.get('numberOfBytes', 0),
        'species': species,
        'modalities': modalities,
        'standards': standards,
        'license': ', '.join(licenses) or '—',
        'published': published,
    }


# --- SVG composition ---------------------------------------------------------
def _build_svg(data: dict) -> str:
    title = escape(data['title'])
    doi = escape(data['doi'])
    identifier = escape(data['identifier'])
    version = escape(data['version'])
    published = escape(data['published'])

    desc_text = _truncate_at_word(data['description'], 240)
    desc_lines = _wrap(desc_text, 60)
    desc_tspans = '\n'.join(
        f'<tspan x="120" dy="{40 if i else 0}">{escape(line)}</tspan>'
        for i, line in enumerate(desc_lines)
    )

    contributors_line = escape(_truncate_contributors(data['contributors'], max_chars=80))

    standards = data['standards']
    standards_label = 'Standards' if len(standards) > 1 else 'Standard'
    standards_value = ' · '.join(standards) if standards else '—'
    modalities_value = ' · '.join(data['modalities']) or '—'
    species_value = '; '.join(data['species']) or '—'

    stats: list[tuple[str, str]] = [
        ('Files', _fmt_count(data['file_count'])),
        ('Size', _fmt_size(data['size_bytes'])),
        (standards_label, standards_value),
        ('License', escape(data['license'])),
        ('Species', escape(species_value)),
        ('Modalities', escape(modalities_value)),
    ]

    stat_rows: list[str] = []
    y0 = 360
    for i, (label, value) in enumerate(stats):
        y = y0 + i * 80
        stat_rows.append(
            f'<text x="1280" y="{y}" font-family="Inter, Helvetica, Arial, sans-serif"'
            f' font-size="22" fill="{MUTED}" font-weight="500"'
            f' letter-spacing="2">{escape(label).upper()}</text>'
            f'<text x="1280" y="{y + 36}" font-family="Inter, Helvetica, Arial, sans-serif"'
            f' font-size="32" fill="{INK}" font-weight="600">{escape(value)}</text>'
        )

    landing_url = f'https://dandiarchive.org/dandiset/{data["identifier"]}/{data["version"]}'
    qr_block = _qr_svg(landing_url, size=140)

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <rect width="{W}" height="{H}" fill="{BG}"/>
  <rect x="0" y="0" width="{W}" height="8" fill="{CORAL}"/>

  <svg x="1480" y="50" width="320" height="128" viewBox="0 0 3341 1341"
       preserveAspectRatio="xMaxYMid meet">{_LOGO_SVG_INLINED_INNER}</svg>

  <g transform="translate(120, 170)">
    <rect width="280" height="48" rx="6" fill="{NAVY}"/>
    <text x="140" y="32" text-anchor="middle"
          font-family="Inter, Helvetica, Arial, sans-serif"
          font-size="22" font-weight="700" fill="white"
          letter-spacing="2">DANDI:{identifier}</text>
  </g>

  <text x="120" y="290" font-family="Inter, Helvetica, Arial, sans-serif"
        font-size="64" font-weight="800" fill="{INK}">{title}</text>

  <text y="380" font-family="Inter, Helvetica, Arial, sans-serif"
        font-size="28" fill="{INK}" font-weight="400">{desc_tspans}</text>

  <text x="120" y="560" font-family="Inter, Helvetica, Arial, sans-serif"
        font-size="20" fill="{MUTED}" font-weight="600"
        letter-spacing="2">CONTRIBUTORS</text>
  <text x="120" y="605" font-family="Inter, Helvetica, Arial, sans-serif"
        font-size="24" fill="{INK}" font-weight="500">{contributors_line}</text>

  <text x="120" y="650" font-family="Inter, Helvetica, Arial, sans-serif"
        font-size="20" fill="{MUTED}" font-weight="600"
        letter-spacing="2">CITE THIS DATASET</text>
  <text x="120" y="698" font-family="JetBrains Mono, Menlo, monospace"
        font-size="26" fill="{NAVY}" font-weight="600">doi:{doi}</text>
  <text x="120" y="738" font-family="Inter, Helvetica, Arial, sans-serif"
        font-size="20" fill="{MUTED}" font-weight="400">
    Published {published} · v{version}
  </text>

  <g transform="translate(120, 790)">{qr_block}</g>
  <text x="290" y="830" font-family="Inter, Helvetica, Arial, sans-serif"
        font-size="20" fill="{MUTED}" font-weight="600"
        letter-spacing="2">SCAN OR VISIT</text>
  <text x="290" y="870" font-family="JetBrains Mono, Menlo, monospace"
        font-size="22" fill="{NAVY}" font-weight="600"
        >dandiarchive.org/dandiset/{identifier}</text>

  <rect x="1240" y="270" width="560" height="640" rx="12" fill="{PANEL}"/>
  <rect x="1240" y="270" width="6" height="640" rx="3" fill="{CORAL}"/>
  <text x="1280" y="330" font-family="Inter, Helvetica, Arial, sans-serif"
        font-size="20" fill="{CORAL}" font-weight="700"
        letter-spacing="3">DATASET</text>
  {''.join(stat_rows)}

  <rect x="0" y="{H - 4}" width="{W}" height="4" fill="{NAVY}"/>
</svg>
"""


def render_shareable_slide_svg(version: Version) -> str:
    """Render the shareable slide for a published Version as an SVG document."""
    data = _extract_data(version)
    return _build_svg(data)
