import request from './request'

export function getDistributionAdjustments(cycleId) {
  return request.get(`/reports/cycle/${cycleId}/distribution-adjustments`)
}

export function getDistributionOverrides(cycleId) {
  const params = cycleId ? `?cycle_id=${cycleId}` : ''
  return request.get(`/approvals/distribution-overrides${params}`)
}

export function approveDistributionOverride(recordId) {
  return request.post(`/approvals/distribution-overrides/${recordId}/approve`)
}

export function rejectDistributionOverride(recordId) {
  return request.post(`/approvals/distribution-overrides/${recordId}/reject`)
}
