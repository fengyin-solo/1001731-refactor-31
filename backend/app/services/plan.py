"""点检计划业务规则：字段校验与筛选调用统一状态口径。"""
from __future__ import annotations

from typing import Any

from app.services import plan_workflow as workflow
from app.store import store

MODULE = "plan"
REQUIRED_FIELDS = ["计划编号", "点检对象", "点检周期"]
STATUS_ORDER = list(workflow.STATUS_SEQUENCE)
ACTION_RULES = dict(workflow.APPROVAL_ACTIONS)
NEGATIVE_ACTIONS = [action for action, status in ACTION_RULES.items() if workflow.is_abnormal_status(status)]


class PlanService:
    def _filtered_rows(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        rows = store.rows(MODULE)
        if keyword:
            rows = [row for row in rows if keyword in str(row.get("计划编号", ""))]
        if status:
            expected = workflow.normalize_status(status)
            rows = [row for row in rows if workflow.current_status(row) == expected]
        return rows

    def list_entries(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = self._filtered_rows(keyword=keyword, status=status)
        total = len(rows)
        start = max(page - 1, 0) * size
        page_rows = [workflow.present_entry(row) for row in rows[start:start + size]]
        return page_rows, total

    def stats(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        """统计与列表使用同一个筛选集合，避免分页或口径不同导致数字对不上。"""
        rows = self._filtered_rows(keyword=keyword, status=status)
        counts = workflow.status_counts(rows)
        return {
            "total": len(rows),
            "pending_approval": counts.get(workflow.PENDING_APPROVAL_STATUS, 0),
            "approved": counts.get(workflow.APPROVED_STATUS, 0),
            "pending": sum(1 for row in rows if workflow.is_pending_status(workflow.current_status(row))),
            "abnormal": sum(1 for row in rows if workflow.is_abnormal_status(workflow.current_status(row))),
            "status_counts": counts,
        }

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None
        return workflow.present_entry(entry)

    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        missing = [field for field in REQUIRED_FIELDS if not str(values.get(field) or "").strip()]
        if missing:
            return None, missing
        rows = store.rows(MODULE)
        entry = {"id": max((int(row.get("id", 0)) for row in rows), default=0) + 1}
        entry.update({field: values.get(field) for field in REQUIRED_FIELDS})
        entry["status"] = workflow.INITIAL_STATUS
        entry["pending"] = workflow.is_pending_status(workflow.INITIAL_STATUS)
        entry["abnormal"] = workflow.is_abnormal_status(workflow.INITIAL_STATUS)
        rows.append(entry)
        return workflow.present_entry(entry), []

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"点检计划 {entry_id} 不存在或已归档"
        target = workflow.target_status_for_action(action)
        if target is None:
            return None, f"动作「{action}」不属于点检计划可执行范围"
        if not workflow.is_known_status(target):
            return None, f"目标状态「{target}」不在允许的状态序列里"
        entry["status"] = target
        entry["pending"] = workflow.is_pending_status(target)
        entry["abnormal"] = workflow.is_abnormal_status(target)
        return workflow.present_entry(entry), f"点检计划已{action}"

    def workflow_rules(self) -> dict[str, Any]:
        return workflow.workflow_rules()
