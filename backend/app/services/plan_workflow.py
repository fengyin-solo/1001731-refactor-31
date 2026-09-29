"""点检计划状态序列与审批规则的唯一口径。

列表筛选、明细展示、动作流转和统计计数都必须使用这里的方法，避免同一计划在不同
接口里得到不同结论。优先级约定：

1. 当前计划状态以 ``status`` 对应的状态序列当前环节为准；历史展示字段「计划状态」
   若与它不一致，只作为旧数据兼容，不参与当前校验。
2. 已经形成的历史审批结论不按新规则重算；历史别名只用于把旧值识别到当前序列。
3. 当前待办、异常和统计口径按本文件的当前状态规则实时计算，因此统计数与列表一致。
"""
from __future__ import annotations

from typing import Any

# 状态序列：新增状态只能调整这里，列表、动作、前端规则和统计会自动跟随。
STATUS_SEQUENCE: tuple[str, ...] = ("待编制", "待审批", "已批复", "已作废")
INITIAL_STATUS = STATUS_SEQUENCE[0]
PENDING_APPROVAL_STATUS = "待审批"
APPROVED_STATUS = "已批复"

# 状态环节上的当前审批口径。
PENDING_STATUSES = frozenset(("待编制", "待审批"))
TERMINAL_STATUSES = frozenset(("已批复", "已作废"))
ABNORMAL_STATUSES = frozenset(("已作废",))

# 动作与目标环节保持为显式映射；不按动作名称推断状态。
APPROVAL_ACTIONS: dict[str, str] = {
    "提交审批": "待审批",
    "确认批复": "已批复",
    "作废计划": "已作废",
}

# 旧版本数据里的状态别名只做识别，不改变已经落库的历史审批事实。
LEGACY_STATUS_ALIASES: dict[str, str] = {
    "待批复": "待审批",
    "已审批": "已批复",
    "作废": "已作废",
}


def normalize_status(value: Any) -> str:
    """把当前或历史状态值识别为当前状态序列中的环节。

    无法识别的历史值原样保留，避免把未知历史审批数据强行改写成当前状态。
    """
    status = str(value or "").strip()
    if not status:
        return INITIAL_STATUS
    if status in STATUS_SEQUENCE:
        return status
    return LEGACY_STATUS_ALIASES.get(status, status)


def current_status(entry: dict[str, Any]) -> str:
    """取计划当前环节；状态序列优先于历史展示字段「计划状态」。"""
    return normalize_status(entry.get("status"))


def is_known_status(status: Any) -> bool:
    return str(status or "").strip() in STATUS_SEQUENCE


def is_pending_status(status: Any) -> bool:
    return normalize_status(status) in PENDING_STATUSES


def is_terminal_status(status: Any) -> bool:
    return normalize_status(status) in TERMINAL_STATUSES


def is_abnormal_status(status: Any) -> bool:
    return normalize_status(status) in ABNORMAL_STATUSES


def target_status_for_action(action: str) -> str | None:
    """按统一审批映射返回动作的目标环节，未知动作不猜测。"""
    return APPROVAL_ACTIONS.get(str(action or "").strip())


def present_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """生成列表和详情共用的计划展示结构，不改变点检周期等业务字段写法。"""
    result = dict(entry)
    status = current_status(result)
    result["status"] = status
    if "计划状态" in result:
        result["计划状态"] = status
    result["pending"] = is_pending_status(status)
    result["abnormal"] = is_abnormal_status(status)
    return result


def status_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    """按状态序列统计；未知历史状态单列，保证各筛选列表合计仍等于全量总数。"""
    counts = {status: 0 for status in STATUS_SEQUENCE}
    for row in rows:
        status = current_status(row)
        counts[status] = counts.get(status, 0) + 1
    return counts


def workflow_rules() -> dict[str, Any]:
    """给前端提供唯一的状态和按钮规则来源。"""
    return {
        "statuses": list(STATUS_SEQUENCE),
        "initial_status": INITIAL_STATUS,
        "actions": list(APPROVAL_ACTIONS.keys()),
        "action_targets": dict(APPROVAL_ACTIONS),
        # 保持当前界面表现：每行仍展示同一组动作，是否允许由动作接口统一校验。
        "available_actions": {
            status: list(APPROVAL_ACTIONS.keys()) for status in STATUS_SEQUENCE
        },
    }
