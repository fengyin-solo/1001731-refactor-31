"""点检计划统一状态口径。

点检计划的状态序列、审批动作与统计判断只能在这里定义一份，列表筛选、
明细读取、动作流转与待办/异常统计全部调用本模块，避免各处各写一套条件
后互相打架。

冲突时的优先级：
1. 当前状态一律以 :data:`STATUS_ORDER` 状态序列里该计划所处的当前环节为准
   （以行内 ``status`` 字段为唯一事实来源），不看历史遗留的标记位；
2. 历史审批口径按当时规则保留：落在状态序列之外的旧状态不改写、不强行
   归并，其 ``pending``/``abnormal`` 仍沿用行内当时写下的标记位。
"""
from __future__ import annotations

from typing import Any

# 点检计划在数据仓库中的模块名。
MODULE = "plan"
# 状态序列：计划当前所处环节，顺序即编制 → 审批 → 批复 → 作废。
STATUS_ORDER: list[str] = ["待编制", "待审批", "已批复", "已作废"]
# 新登记计划进入的首个环节。
INITIAL_STATUS = STATUS_ORDER[0]
# 审批流转动作与目标环节的一一对应，流转表现保持不变。
ACTION_RULES: dict[str, str] = {
    "提交审批": "待审批",
    "确认批复": "已批复",
    "作废计划": "已作废",
}
# 仍需处理的环节：终态（已作废）与已批复之外的在途环节都算待办。
PENDING_STATUSES: frozenset[str] = frozenset({"待编制", "待审批"})
# 异常环节：只有作废属于异常口径。
ABNORMAL_STATUSES: frozenset[str] = frozenset({"已作废"})
# 待审统计卡片对应的环节。
PENDING_REVIEW_STATUS = "待审批"
# 已批复统计卡片对应的环节。
APPROVED_STATUS = "已批复"


def is_known_status(status: Any) -> bool:
    """状态是否落在当前状态序列内；序列外的旧状态按历史口径保留。"""
    return status in STATUS_ORDER


def is_pending_status(status: Any) -> bool:
    """当前环节是否属于待办口径；序列外状态交还给历史标记位判断。"""
    return status in PENDING_STATUSES


def is_abnormal_status(status: Any) -> bool:
    """当前环节是否属于异常口径；序列外状态交还给历史标记位判断。"""
    return status in ABNORMAL_STATUSES


def target_of_action(action: str) -> str | None:
    """取审批动作的目标环节；非审批动作返回 None。"""
    return ACTION_RULES.get(action)


def present_row(row: dict[str, Any]) -> dict[str, Any]:
    """按统一口径补全一条计划的对外字段（列表与明细共用）。

    状态序列内的计划，``pending``/``abnormal`` 一律由当前环节重新导出，
    保证统计与列表对得上；序列外的历史计划原样保留行内标记位。
    """
    presented = dict(row)
    status = presented.get("status")
    if is_known_status(status):
        presented["pending"] = is_pending_status(status)
        presented["abnormal"] = is_abnormal_status(status)
    return presented


def count_by_status(rows: list[dict[str, Any]], status: str) -> int:
    """统计处于指定环节的计划数：与列表按该状态筛选的口径完全一致。"""
    return sum(1 for row in rows if row.get("status") == status)


def row_is_pending(row: dict[str, Any]) -> bool:
    """一条计划是否算待办：序列内按当前环节判，序列外沿用历史标记位。"""
    status = row.get("status")
    if is_known_status(status):
        return is_pending_status(status)
    return bool(row.get("pending"))


def row_is_abnormal(row: dict[str, Any]) -> bool:
    """一条计划是否算异常：序列内按当前环节判，序列外沿用历史标记位。"""
    status = row.get("status")
    if is_known_status(status):
        return is_abnormal_status(status)
    return bool(row.get("abnormal"))
