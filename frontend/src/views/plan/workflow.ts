/** 点检计划状态与审批动作统一从后端规则接口获取，前端不再另写一份。 */
export type PlanWorkflowRules = {
  statuses: string[]
  initial_status: string
  actions: string[]
  action_targets: Record<string, string>
  available_actions: Record<string, string[]>
}

export type PlanStats = {
  total: number
  pending_approval: number
  approved: number
  pending: number
  abnormal: number
  status_counts: Record<string, number>
}

export const defaultWorkflowRules: PlanWorkflowRules = {
  statuses: [],
  initial_status: '',
  actions: [],
  action_targets: {},
  available_actions: {},
}

export function actionsForStatus(rules: PlanWorkflowRules, status: string): string[] {
  return rules.available_actions[status] ?? rules.actions
}
