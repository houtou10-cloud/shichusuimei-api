import pytest

from engine.hour import calculate_hour_pillar


@pytest.mark.parametrize(
    "day_stem,expected",
    [
        ("甲", "乙亥"),
        ("乙", "丁亥"),
        ("丙", "己亥"),
        ("丁", "辛亥"),
        ("戊", "癸亥"),
        ("己", "乙亥"),
        ("庚", "丁亥"),
        ("辛", "己亥"),
        ("壬", "辛亥"),
        ("癸", "癸亥"),
    ],
)
def test_hour_pillar_hai_for_all_day_stems(
    day_stem,
    expected,
):
    result = calculate_hour_pillar(
        day_stem=day_stem,
        hour=21,
    )

    assert result == expected
