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


def test_chart_contains_hidden_stems_and_ten_gods():
    request = make_request(
        birth_date="1985-07-17",
        birth_time="21:50",
        birth_place="石川県",
        gender="female",
    )

    result = calculate_chart(request)
    chart = result["chart"]

    assert chart["year"]["stem_ten_god"] == "比肩"
    assert chart["year"]["hidden_stems"] == [
        "己",
        "癸",
        "辛",
    ]
    assert (
        chart["year"]["main_hidden_stem"]
        == "己"
    )
    assert (
        chart["year"]["main_hidden_stem_ten_god"]
        == "偏財"
    )

    assert chart["month"]["stem_ten_god"] == "偏印"
    assert chart["month"]["main_hidden_stem"] == "己"
    assert (
        chart["month"]["main_hidden_stem_ten_god"]
        == "偏財"
    )

    assert chart["day"]["stem_ten_god"] is None
    assert chart["day"]["main_hidden_stem"] == "丙"
    assert (
        chart["day"]["main_hidden_stem_ten_god"]
        == "傷官"
    )

    assert chart["hour"]["stem_ten_god"] == "食神"
    assert chart["hour"]["main_hidden_stem"] == "壬"
    assert (
        chart["hour"]["main_hidden_stem_ten_god"]
        == "印綬"
    )

def test_chart_contains_twelve_stages():
    request = make_request(
        birth_date="1985-07-17",
        birth_time="21:50",
        birth_place="石川県",
        gender="female",
    )

    result = calculate_chart(request)
    chart = result["chart"]

    assert chart["year"]["twelve_stage"] == "衰"
    assert chart["month"]["twelve_stage"] == "養"
    assert chart["day"]["twelve_stage"] == "沐浴"
    assert chart["hour"]["twelve_stage"] == "死"

def test_chart_contains_root_strength():
    request = make_request(
        birth_date="1985-07-17",
        birth_time="21:50",
        birth_place="石川県",
        gender="female",
    )

    result = calculate_chart(request)

    root_strength = result[
        "root_strength"
    ]

    assert root_strength[
        "has_root"
    ] is True

    assert root_strength[
        "root_count"
    ] == 2

    assert root_strength[
        "root_positions"
    ] == [
        "month",
        "hour",
    ]

def test_chart_contains_month_command():
    request = make_request(
        birth_date="1985-07-17",
        birth_time="21:50",
        birth_place="石川県",
        gender="female",
    )

    result = calculate_chart(request)

    month_command = result[
        "month_command"
    ]

    assert month_command[
        "day_element"
    ] == "木"

    assert month_command[
        "month_branch"
    ] == "未"

    assert month_command[
        "month_element"
    ] == "土"

    assert month_command[
        "relationship"
    ] == "wealth"

    assert month_command[
        "supports_day_master"
    ] is False
