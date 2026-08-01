import pytest


@pytest.mark.skip(
    reason=(
        "JPL天体暦ファイルの外部ダウンロードが"
        "タイムアウトするため一時停止"
    )
)
def test_get_season_events():
    pass
