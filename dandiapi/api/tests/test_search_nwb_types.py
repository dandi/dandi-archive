from __future__ import annotations

import pytest

from dandiapi.api.services.search.nwb_types import expand_technique, expand_variable

pytestmark = pytest.mark.ai_generated

_PATCH_CLAMP_SUBTYPES = {
    'PatchClampSeries',
    'CurrentClampSeries',
    'CurrentClampStimulusSeries',
    'IZeroClampSeries',
    'VoltageClampSeries',
    'VoltageClampStimulusSeries',
}


@pytest.mark.parametrize(
    ('value', 'expected'),
    [
        ('PatchClampSeries', _PATCH_CLAMP_SUBTYPES),
        ('patchclampseries', _PATCH_CLAMP_SUBTYPES),
        ('CurrentClampSeries', {'CurrentClampSeries', 'IZeroClampSeries'}),
        # A type with no parent or subtypes (now that NWBDataInterface is
        # dropped) has nothing to expand to; the substring match covers it.
        ('LFP', set()),
        ('EventWaveform', set()),
        # Not an exact type name: no expansion (the substring match still applies).
        ('clamp', set()),
        ('nosuchtype', set()),
    ],
)
def test_expand_variable(value, expected):
    assert expand_variable(value) == expected


def test_expand_variable_includes_deep_descendants():
    # CurrentClampSeries -> PatchClampSeries -> TimeSeries
    assert expand_variable('TimeSeries') >= _PATCH_CLAMP_SUBTYPES


@pytest.mark.parametrize(
    'value',
    [
        'AlignedDynamicTable',
        'Container',
        'Data',
        'DynamicTable',
        'dynamictable',
        'NWBContainer',
        'NWBData',
        'NWBDataInterface',
        'VectorData',
    ],
)
def test_expand_variable_skips_generic_base_types(value):
    # Nearly every dandiset has subtypes of these, so they're left out of the
    # hierarchy snapshot and must not expand.
    assert expand_variable(value) == set()


@pytest.mark.parametrize(
    ('value', 'expected'),
    [
        (
            'patch clamp',
            {'patch clamp technique', 'current clamp technique', 'voltage clamp technique'},
        ),
        ('current clamp', {'current clamp technique'}),
        ('spike sorting', {'spike sorting technique'}),
        ('nosuchtechnique', set()),
    ],
)
def test_expand_technique(value, expected):
    assert expand_technique(value) == expected
