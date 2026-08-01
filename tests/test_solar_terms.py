from engine.solar_terms import get_season_events


def test_get_season_events():
    results = get_season_events(1984)

    assert len(results) == 4

    names = [item["name"] for item in results]

    assert names == [
        "春分",
        "夏至",
        "秋分",
        "冬至",
    ]
