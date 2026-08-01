from types import SimpleNamespace

from engine.chart import calculate_chart


def make_request(
    birth_date: str,
    birth_time: str | None,
    birth_place: str,
    gender: str,
):
    return SimpleNamespace(
        birth_date=birth_date,
        birth_time=birth_time,
        birth_place=birth_place,
        gender=gender,
    )


def test_chart_1984_early_hour():
    request = make_request(
        birth_date="1984-07-22",
        birth_time="04:15",
        birth_place="北海道",
        gender="female",
    )

    result = calculate_chart(request)

    assert result["chart"]["year"]["pillar"] == "甲子"
    assert result["chart"]["month"]["pillar"] == "辛未"
    assert result["chart"]["day"]["pillar"] == "乙巳"
    assert result["chart"]["hour"]["pillar"] == "戊寅"
    assert result["day_master"]["stem"] == "乙"


def test_chart_1984_afternoon():
    request = make_request(
        birth_date="1984-07-22",
        birth_time="13:40",
        birth_place="福岡県",
        gender="male",
    )

    result = calculate_chart(request)

    assert result["chart"]["year"]["pillar"] == "甲子"
    assert result["chart"]["month"]["pillar"] == "辛未"
    assert result["chart"]["day"]["pillar"] == "乙巳"
    assert result["chart"]["hour"]["pillar"] == "癸未"


def test_chart_1985():
    request = make_request(
        birth_date="1985-07-17",
        birth_time="21:50",
        birth_place="石川県",
        gender="female",
    )

    result = calculate_chart(request)

    assert result["chart"]["year"]["pillar"] == "乙丑"
    assert result["chart"]["month"]["pillar"] == "癸未"
    assert result["chart"]["day"]["pillar"] == "乙巳"
    assert result["chart"]["hour"]["pillar"] == "丁亥"


def test_chart_without_birth_time():
    request = make_request(
        birth_date="1984-07-22",
        birth_time=None,
        birth_place="東京都",
        gender="male",
    )

    result = calculate_chart(request)

    assert result["chart"]["year"]["pillar"] == "甲子"
    assert result["chart"]["month"]["pillar"] == "辛未"
    assert result["chart"]["day"]["pillar"] == "乙巳"
    assert result["chart"]["hour"] is None

    assert any(
        "出生時間が不明" in warning
        for warning in result["warnings"]
    )
