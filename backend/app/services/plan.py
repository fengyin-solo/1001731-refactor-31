"""点检计划业务规则：状态流转、字段校验与筛选口径统一走 plan_rules。"""
from __future__ import annotations

from typing import Any

from app.services import plan_rules
from app.store import store

MODULE = "plan"
REQUIRED_FIELDS = ["计划编号", "点检对象", "点检周期"]


class PlanService:
    def list_entries(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = store.rows(MODULE)
        if keyword:
            rows = [row for row in rows if keyword in str(row.get("计划编号", ""))]
        if status:
            rows = [row for row in rows if row.get("status") == status]
        total = len(rows)
        start = max(page - 1, 0) * size
        page_rows = rows[start:start + size]
        return [plan_rules.present_row(row) for row in page_rows], total

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        row = store.find(MODULE, entry_id)
        if row is None:
            return None
        return plan_rules.present_row(row)

    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        missing = [field for field in REQUIRED_FIELDS if not str(values.get(field) or "").strip()]
        if missing:
            return None, missing
        rows = store.rows(MODULE)
        entry = {"id": max((int(row.get("id", 0)) for row in rows), default=0) + 1}
        entry.update({field: values.get(field) for field in REQUIRED_FIELDS})
        entry["status"] = plan_rules.INITIAL_STATUS
        entry["pending"] = plan_rules.is_pending_status(plan_rules.INITIAL_STATUS)
        entry["abnormal"] = plan_rules.is_abnormal_status(plan_rules.INITIAL_STATUS)
        rows.append(entry)
        return plan_rules.present_row(entry), []

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"点检计划 {entry_id} 不存在或已归档"
        target = plan_rules.target_of_action(action)
        if target is None:
            return None, f"动作「{action}」不属于点检计划可执行范围"
        if not plan_rules.is_known_status(target):
            return None, f"目标状态「{target}」不在允许的状态序列里"
        entry["status"] = target
        # 当前环节是唯一事实来源：标记位随当前环节导出，不再按“是否最后一项”猜。
        entry["pending"] = plan_rules.is_pending_status(target)
        entry["abnormal"] = plan_rules.is_abnormal_status(target)
        return plan_rules.present_row(entry), f"点检计划已{action}"

    def status_summary(self) -> dict[str, int]:
        """待审/已批复统计，直接复用列表的状态筛选口径，保证数与列表对得上。"""
        rows = store.rows(MODULE)
        return {
            "待审批": plan_rules.count_by_status(rows, plan_rules.PENDING_REVIEW_STATUS),
            "已批复": plan_rules.count_by_status(rows, plan_rules.APPROVED_STATUS),
        }
