def test_chart_contains_month_command():
    request = make_request(
        birth_date="1985-07-17",
        birth_time="21:50",
        birth_place="石川県",
        gender="female",
    )

    result = calculate_chart(request)

    month_command = result["month_command"]

    assert month_command["day_stem"] == "乙"
    assert month_command["day_element"] == "木"
    assert month_command["month_branch"] == "未"
    assert month_command["month_element"] == "土"
    assert month_command["relationship"] == "wealth"
    assert month_command["relationship_label"] == "財星"
    assert month_command["effect"] == "draining"
    assert month_command["supports_day_master"] is False
