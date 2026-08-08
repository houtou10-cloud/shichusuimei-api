from datetime import date, datetime
from zoneinfo import ZoneInfo


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

from engine.branch_relations import (
    find_branch_clashes,
    find_branch_combinations,

)
from engine.day_master_strength import (
    classify_five_elements_for_day_master,
    classify_weighted_elements_for_day_master,
)
from engine.five_elements import calculate_five_elements
from engine.final_strength_judgment import (
    evaluate_final_strength_judgment,
)
from engine.integrated_month_strength import (
    calculate_integrated_month_strength,
)
from engine.month_command import (
    classify_month_relationship,
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


def calculate_chart(req) -> dict:
    """
    APIの入力情報から命式と各種分析データを作成します。
    """
    birth_date = normalize_birth_date(
        req.birth_date
    )

    birth_time = normalize_birth_time(
        req.birth_time
    )

    warnings: list[str] = []

    if birth_time is None:
        time_text = "12:00"

        warnings.append(
            "出生時間が不明なため、時柱は計算していません。"
        )
    else:
        time_text = birth_time

    birth_datetime = datetime.strptime(
        f"{birth_date} {time_text}",
        "%Y-%m-%d %H:%M",
    ).replace(
        tzinfo=JST
    )

    pillars = calculate_four_pillars(
        birth_datetime
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

    branch_clashes = find_branch_clashes(
        chart_data

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

    return {
        "input": {
            "birth_date": birth_date,
            "birth_time": birth_time,
            "birth_place": req.birth_place,
            "gender": req.gender,
            "timezone": "Asia/Tokyo",
        },
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
