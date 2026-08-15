from datetime import date, datetime
from zoneinfo import ZoneInfo


from engine.annual_luck import (
    calculate_annual_luck_for_datetime,
)
from engine.branch_relation_strength import (
    calculate_branch_relation_strength,
)
from engine.branch_relations import (
    find_branch_breaks,
    find_branch_clashes,
    find_branch_combinations,
    find_branch_harms,
    find_branch_punishments,
    find_branch_trines,
)
from engine.climate_useful_gods import (
    evaluate_climate_useful_gods,
)
from engine.current_luck import (
    evaluate_current_luck,
)
from engine.integrated_luck import (
    calculate_integrated_luck,
)
from engine.day_master_strength import (
    classify_five_elements_for_day_master,
    classify_weighted_elements_for_day_master,
)
from engine.five_elements import (
    calculate_five_elements,
)
from engine.final_strength_judgment import (
    evaluate_final_strength_judgment,
)
from engine.integrated_month_strength import (
    calculate_integrated_month_strength,
)
from engine.luck_pillars import (
    calculate_luck_pillars,
)
from engine.month_command import (
    classify_month_relationship,
)
from engine.pattern_candidates import (
    evaluate_pattern_candidates,
)
from engine.pattern_judgment import (
    evaluate_pattern_judgment,
)
from engine.pattern_useful_gods import (
    evaluate_pattern_useful_gods,
)
from engine.pattern_special_rules import (
    evaluate_pattern_special_rules,
)
from engine.pillars import calculate_four_pillars
from engine.root_strength import find_roots
from engine.seasonal_strength import (
    evaluate_seasonal_strength,
)
from engine.stem_combination_conflict_types import (
    evaluate_stem_combination_conflict_types,
)
from engine.stem_combination_conflicts import (
    evaluate_stem_combination_conflicts,
)
from engine.stem_combinations import (
    find_stem_combinations,
)
from engine.stem_transformation_judgment import (
    evaluate_stem_transformation_judgment,
)
from engine.stem_transformation import (
    evaluate_stem_transformations,
)
from engine.strength_judgment import (
    calculate_provisional_strength,
    calculate_weighted_provisional_strength,
)
from engine.transformation_exposure import (
    evaluate_transformation_exposures,
)
from engine.transformation_root import (
    evaluate_transformation_roots,
)
from engine.useful_gods import (
    evaluate_useful_gods_v3,
)
from engine.weighted_five_elements import (
    calculate_weighted_five_elements,
)
from engine.weighted_month_command import (
    calculate_weighted_month_command,
)
from engine.weighted_root_strength import (
    calculate_weighted_roots,
)


JST = ZoneInfo("Asia/Tokyo")


def normalize_birth_date(
    value: str | date,
) -> str:
    """
    birth_dateをYYYY-MM-DD形式の文字列へ統一します。
    """
    if isinstance(value, date):
        return value.isoformat()

    if isinstance(value, str):
        try:
            datetime.strptime(
                value,
                "%Y-%m-%d",
            )
        except ValueError as error:
            raise ValueError(
                "birth_dateはYYYY-MM-DD形式で指定してください。"
            ) from error

        return value

    raise TypeError(
        "birth_dateは文字列またはdate型で指定してください。"
    )


def normalize_birth_time(
    value: str | None,
) -> str | None:
    """
    birth_timeをHH:MM形式として検証します。

    None は出生時刻不明として正式に許可します。
    """
    if value is None:
        return None

    if not isinstance(value, str):
        raise TypeError(
            "birth_timeはHH:MM形式の文字列で指定してください。"
        )

    try:
        datetime.strptime(
            value,
            "%H:%M",
        )
    except ValueError as error:
        raise ValueError(
            "birth_timeはHH:MM形式で指定してください。"
        ) from error

    return value


def build_birth_time_status(
    birth_time: str | None,
) -> dict:
    """
    出生時刻の既知・未知状態と、
    その状態による計算・解釈範囲を返します。

    この情報は計算結果そのものを書き換えるためではなく、
    reading_context・AI鑑定・PDFなどの上位層が
    出生時刻不明時の不確実性を正しく扱うために使用します。

    出生時刻あり:
        ・四柱すべて利用可能
        ・通常の命式解釈
        ・大運開始時期を通常精度で扱う

    出生時刻不明:
        ・年柱、月柱、日柱のみ利用可能
        ・時柱は生成結果から除外
        ・五行、通根、身強身弱、格局、用神などは
          確認可能な三柱範囲での評価
        ・大運の順逆、干支列は利用可能
        ・大運開始年齢、開始日時、現在大運の境界判定は
          出生時刻不明による精度制限あり
    """
    known = birth_time is not None

    if known:
        return {
            "known": True,
            "hour_pillar_available": True,
            "calculation_scope": "four_pillars",
            "interpretation_scope": "full_chart",
            "five_elements_scope": "full_chart",
            "root_scope": "full_chart",
            "strength_scope": "full_chart",
            "pattern_scope": "full_chart",
            "useful_gods_scope": "full_chart",
            "relationship_scope": "full_chart",
            "luck_pillar_sequence_available": True,
            "luck_start_timing_precision": "normal",
            "current_luck_precision": "normal",
            "internal_reference_time_used": False,
            "internal_reference_time": None,
            "is_provisional_due_to_unknown_birth_time": False,
        }

    return {
        "known": False,
        "hour_pillar_available": False,
        "calculation_scope": "three_pillars",
        "interpretation_scope": "known_pillars_only",
        "five_elements_scope": "known_pillars_only",
        "root_scope": "known_pillars_only",
        "strength_scope": "known_pillars_only",
        "pattern_scope": "known_pillars_only",
        "useful_gods_scope": "known_pillars_only",
        "relationship_scope": "known_pillars_only",
        "luck_pillar_sequence_available": True,
        "luck_start_timing_precision": "estimated",
        "current_luck_precision": "estimated",
        "internal_reference_time_used": True,
        "internal_reference_time": "12:00",
        "is_provisional_due_to_unknown_birth_time": True,
    }


def calculate_chart(
    req,
    target_datetime: datetime | None = None,
) -> dict:
    """
    APIの入力情報から命式と各種分析データを作成します。

    target_datetime:
        現在大運を判定する基準日時。

        None の場合は Asia/Tokyo の現在日時を使用します。
        テストでは固定日時を渡すことで再現性を確保できます。

    出生時刻不明:
        birth_time=None を正式に許可します。

        年柱・月柱・日柱を計算するため、
        内部計算上のみ12:00を代表時刻として使用します。

        この12:00は実際の出生時刻ではありません。

        時柱は最終的なchartから除外し、
        birth_time_statusによって三柱範囲の計算であることを
        上位層へ明示します。

        現行の大運計算エンジンはbirth_datetimeを必要とするため、
        出生時刻不明の場合は内部代表時刻12:00を使用します。

        そのため大運開始年齢・開始日時・現在大運の境界判定は
        birth_time_statusでestimatedとして明示します。
    """
    birth_date = normalize_birth_date(
        req.birth_date
    )

    birth_time = normalize_birth_time(
        req.birth_time
    )

    birth_time_status = (
        build_birth_time_status(
            birth_time
        )
    )

    warnings: list[str] = []

    if birth_time is None:
        calculation_time_text = "12:00"

        warnings.append(
            "出生時間が不明なため、時柱は計算していません。"
        )

        warnings.append(
            "出生時間が不明なため、五行・通根・身強身弱・格局・用神などは"
            "確認可能な年柱・月柱・日柱の範囲での評価です。"
        )

        warnings.append(
            "出生時間が不明なため、大運開始年齢・開始日時・"
            "現在大運の切り替わり時期には精度上の制限があります。"
        )

    else:
        calculation_time_text = birth_time

    calculation_birth_datetime = (
        datetime.strptime(
            f"{birth_date} {calculation_time_text}",
            "%Y-%m-%d %H:%M",
        ).replace(
            tzinfo=JST
        )
    )

    pillars = calculate_four_pillars(
        calculation_birth_datetime
    )

    if birth_time is None:
        pillars["hour"] = None

    chart_data = {
        "year": pillars["year"],
        "month": pillars["month"],
        "day": pillars["day"],
        "hour": pillars["hour"],
    }

    stem_combinations = (
        find_stem_combinations(
            chart_data
        )
    )

    stem_combination_conflicts = (
        evaluate_stem_combination_conflicts(
            stem_combinations,
            chart_data,
        )
    )

    stem_combination_conflict_types = (
        evaluate_stem_combination_conflict_types(
            stem_combination_conflicts
        )
    )

    stem_transformations = (
        evaluate_stem_transformations(
            stem_combinations,
            chart_data,
        )
    )

    transformation_roots = (
        evaluate_transformation_roots(
            stem_transformations,
            chart_data,
        )
    )

    transformation_exposures = (
        evaluate_transformation_exposures(
            stem_transformations,
            chart_data,
        )
    )

    stem_transformation_judgment = (
        evaluate_stem_transformation_judgment(
            stem_transformations,
            transformation_roots,
            transformation_exposures,
            stem_combination_conflicts,
            stem_combination_conflict_types,
        )
    )

    five_elements = calculate_five_elements(
        chart_data
    )

    weighted_five_elements = (
        calculate_weighted_five_elements(
            chart_data
        )
    )

    day_master_balance = (
        classify_five_elements_for_day_master(
            pillars["day_master"]["stem"],
            five_elements,
        )
    )

    weighted_day_master_balance = (
        classify_weighted_elements_for_day_master(
            pillars["day_master"]["stem"],
            weighted_five_elements,
        )
    )

    root_strength = find_roots(
        pillars["day_master"]["stem"],
        chart_data,
    )

    weighted_root_strength = (
        calculate_weighted_roots(
            pillars["day_master"]["stem"],
            chart_data,
        )
    )

    branch_clashes = (
        find_branch_clashes(
            chart_data
        )
    )

    branch_combinations = (
        find_branch_combinations(
            chart_data
        )
    )

    branch_trines = (
        find_branch_trines(
            chart_data
        )
    )

    branch_punishments = (
        find_branch_punishments(
            chart_data
        )
    )

    branch_harms = (
        find_branch_harms(
            chart_data
        )
    )

    branch_breaks = (
        find_branch_breaks(
            chart_data
        )
    )

    branch_relation_strength = (
        calculate_branch_relation_strength(
            branch_clashes,
            branch_combinations,
            branch_trines,
            branch_punishments,
            branch_harms,
            branch_breaks,
        )
    )

    month_command = (
        classify_month_relationship(
            pillars["day_master"]["stem"],
            pillars["month"]["branch"],
        )
    )

    weighted_month_command = (
        calculate_weighted_month_command(
            pillars["day_master"]["stem"],
            pillars["month"],
        )
    )

    seasonal_strength = (
        evaluate_seasonal_strength(
            pillars["day_master"]["stem"],
            pillars["month"]["branch"],
        )
    )

    integrated_month_strength = (
        calculate_integrated_month_strength(
            seasonal_strength,
            weighted_month_command,
        )
    )

    strength_judgment = (
        calculate_provisional_strength(
            day_master_balance,
            root_strength,
            month_command,
        )
    )

    weighted_strength_judgment = (
        calculate_weighted_provisional_strength(
            weighted_day_master_balance,
            weighted_root_strength,
            month_command,
            integrated_month_strength,
        )
    )

    warnings.extend(
        pillars.get(
            "warnings",
            [],
        )
    )

    final_strength_judgment = (
        evaluate_final_strength_judgment(
            weighted_strength_judgment,
            weighted_root_strength,
            integrated_month_strength,
            branch_relation_strength,
            stem_transformation_judgment,
        )
    )

    pattern_candidates = (
        evaluate_pattern_candidates(
            chart_data,
            pillars["day_master"]["stem"],
        )
    )

    pattern_special_rules = (
        evaluate_pattern_special_rules(
            chart_data,
            final_strength_judgment,
        )
    )

    pattern_judgment = (
        evaluate_pattern_judgment(
            pattern_candidates,
            final_strength_judgment,
            stem_transformation_judgment,
            branch_relation_strength,
            pattern_special_rules,
        )
    )

    pattern_useful_gods = (
        evaluate_pattern_useful_gods(
            pillars[
                "day_master"
            ][
                "stem"
            ],
            pattern_judgment,
            weighted_five_elements,
        )
    )

    climate_useful_gods = (
        evaluate_climate_useful_gods(
            pillars[
                "day_master"
            ][
                "stem"
            ],
            pillars[
                "month"
            ][
                "branch"
            ],
        )
    )

    useful_gods = (
        evaluate_useful_gods_v3(
            pillars[
                "day_master"
            ][
                "stem"
            ],
            weighted_five_elements,
            final_strength_judgment,
            pattern_judgment,
            climate_useful_gods,
            pattern_useful_gods,
        )
    )

    # solar_terms_v2 は現在 timezone-naive の
    # ローカル日時を使用する。
    #
    # calculation_birth_datetime は JST aware なので、
    # 大運計算へ渡す際は「日本時間の壁時計値」を保ったまま
    # tzinfo のみ外して互換化する。
    #
    # 出生時刻不明の場合、
    # calculation_birth_datetime の時刻部分は内部代表値12:00。
    #
    # これは実際の出生時刻を意味しない。
    # そのため birth_time_status では
    # luck_start_timing_precision / current_luck_precision を
    # estimated として上位層へ伝える。
    luck_birth_datetime = (
        calculation_birth_datetime.replace(
            tzinfo=None
        )
    )

    luck_pillars = (
        calculate_luck_pillars(
            year_stem=pillars[
                "year"
            ][
                "stem"
            ],
            month_ganzhi=pillars[
                "month"
            ][
                "pillar"
            ],
            day_master_stem=pillars[
                "day_master"
            ][
                "stem"
            ],
            gender=req.gender,
            birth_datetime=(
                luck_birth_datetime
            ),
            useful_gods=useful_gods,
        )
    )

    # current_luck_v1 の判定基準日時。
    #
    # 通常API:
    #   target_datetime=None
    #   -> Asia/Tokyo の現在日時
    #
    # テスト:
    #   target_datetime に固定日時を指定
    #   -> 再現可能な現在大運判定
    if target_datetime is None:
        current_target_datetime = (
            datetime.now(
                JST
            )
        )

    else:
        if not isinstance(
            target_datetime,
            datetime,
        ):
            raise TypeError(
                "target_datetimeはdatetime型で指定してください。"
            )

        current_target_datetime = (
            target_datetime
        )

    # calculation_birth_datetime /
    # solar_terms_v2 /
    # current_luck_v1 の現行仕様に合わせ、
    # 日本時間の壁時計値を保持した
    # timezone-naive datetime へ揃える。
    if (
        current_target_datetime.tzinfo
        is not None
        and current_target_datetime.utcoffset()
        is not None
    ):
        current_target_datetime = (
            current_target_datetime.astimezone(
                JST
            ).replace(
                tzinfo=None
            )
        )

    current_luck = (
        evaluate_current_luck(
            birth_datetime=(
                luck_birth_datetime
            ),
            target_datetime=(
                current_target_datetime
            ),
            luck_pillars=(
                luck_pillars
            ),
        )
    )

    # annual_luck_v1
    #
    # current_luck と同じ target_datetime を使用し、
    # 「現在大運」と「現在歳運」の基準時刻を統一する。
    #
    # calculate_annual_luck_for_datetime() 側では、
    # year.py と同じ暫定立春境界
    # （2月4日00:00）を使用する。
    annual_luck = (
        calculate_annual_luck_for_datetime(
            target_datetime=(
                current_target_datetime
            ),
            day_master_stem=pillars[
                "day_master"
            ][
                "stem"
            ],
            useful_gods=(
                useful_gods
            ),
            current_luck=(
                current_luck
            ),
        )
    )

    # integrated_luck_v1
    #
    # 現在大運・歳運・useful_gods_v3 を
    # 既存結果からそのまま統合する。
    integrated_luck = (
        calculate_integrated_luck(
            current_luck=(
                current_luck
            ),
            annual_luck=(
                annual_luck
            ),
            useful_gods=(
                useful_gods
            ),
        )
    )

    # five_year_luck_v1
    # 鑑定基準年を含む5年間を計算する。
    # 初年度は鑑定基準日時、翌年以降は各年7月1日12:00を代表日時とする。
    # 各年で大運を再判定するため、大運切替をまたぐ場合にも対応する。
    five_year_luck = []
    five_year_start_year = current_target_datetime.year

    for year_offset in range(5):
        five_year_year = five_year_start_year + year_offset

        if year_offset == 0:
            five_year_target_datetime = current_target_datetime
        else:
            five_year_target_datetime = datetime(
                five_year_year,
                7,
                1,
                12,
                0,
            )

        five_year_current_luck = evaluate_current_luck(
            birth_datetime=luck_birth_datetime,
            target_datetime=five_year_target_datetime,
            luck_pillars=luck_pillars,
        )

        five_year_annual_luck = calculate_annual_luck_for_datetime(
            target_datetime=five_year_target_datetime,
            day_master_stem=pillars["day_master"]["stem"],
            useful_gods=useful_gods,
            current_luck=five_year_current_luck,
        )

        five_year_integrated_luck = calculate_integrated_luck(
            current_luck=five_year_current_luck,
            annual_luck=five_year_annual_luck,
            useful_gods=useful_gods,
        )

        five_year_luck.append(
            {
                "year": five_year_year,
                "target_datetime": five_year_target_datetime.isoformat(),
                "current_luck": five_year_current_luck,
                "annual_luck": five_year_annual_luck,
                "integrated_luck": five_year_integrated_luck,
            }
        )

    return {
        "input": {
            "birth_date": birth_date,
            "birth_time": birth_time,
            "birth_place": req.birth_place,
            "gender": req.gender,
            "timezone": "Asia/Tokyo",
        },

        # 出生時刻の確度情報。
        #
        # 既存の各計算結果を変更せず、
        # reading_context / AI / PDF が
        # 出生時刻不明時の解釈範囲を判断するために使用する。
        "birth_time_status": (
            birth_time_status
        ),

        "chart": chart_data,

        "stem_combinations": (
            stem_combinations
        ),

        "stem_combination_conflicts": (
            stem_combination_conflicts
        ),

        "stem_combination_conflict_types": (
            stem_combination_conflict_types
        ),

        "stem_transformations": (
            stem_transformations
        ),

        "transformation_roots": (
            transformation_roots
        ),

        "transformation_exposures": (
            transformation_exposures
        ),

        "stem_transformation_judgment": (
            stem_transformation_judgment
        ),

        "final_strength_judgment": (
            final_strength_judgment
        ),

        "pattern_candidates": (
            pattern_candidates
        ),

        "pattern_special_rules": (
            pattern_special_rules
        ),

        "pattern_judgment": (
            pattern_judgment
        ),

        "pattern_useful_gods": (
            pattern_useful_gods
        ),

        "climate_useful_gods": (
            climate_useful_gods
        ),

        "useful_gods": (
            useful_gods
        ),

        "luck_pillars": (
            luck_pillars
        ),

        "current_luck": (
            current_luck
        ),

        "annual_luck": (
            annual_luck
        ),

        "integrated_luck": (
            integrated_luck
        ),

        "five_year_luck": (
            five_year_luck
        ),

        "day_master": pillars["day_master"],

        "five_elements": five_elements,

        "weighted_five_elements": (
            weighted_five_elements
        ),

        "day_master_balance": (
            day_master_balance
        ),

        "weighted_day_master_balance": (
            weighted_day_master_balance
        ),

        "root_strength": root_strength,

        "weighted_root_strength": (
            weighted_root_strength
        ),

        "branch_clashes": (
            branch_clashes
        ),

        "branch_combinations": (
            branch_combinations
        ),

        "branch_trines": (
            branch_trines
        ),

        "branch_punishments": (
            branch_punishments
        ),

        "branch_harms": (
            branch_harms
        ),

        "branch_breaks": (
            branch_breaks
        ),

        "branch_relation_strength": (
            branch_relation_strength
        ),

        "month_command": month_command,

        "weighted_month_command": (
            weighted_month_command
        ),

        "seasonal_strength": (
            seasonal_strength
        ),

        "integrated_month_strength": (
            integrated_month_strength
        ),

        "strength_judgment": (
            strength_judgment
        ),

        "weighted_strength_judgment": (
            weighted_strength_judgment
        ),

        "calculation_rules": (
            pillars["calculation_rules"]
        ),

        "calculation_status": (
            pillars["calculation_status"]
        ),

        "warnings": warnings,
    }