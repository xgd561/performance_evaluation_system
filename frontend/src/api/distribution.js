import request from './request'

export function getDistributionAdjustments(cycleId) {
  return request.get(`/reports/cycle/${cycleId}/distribution-adjustments`)
}

export function getDistributionOverrides(cycleId) {
  return request.get('/approvals/distribution-overrides', { params: { cycle_id: cycleId } })
}

export function approveDistributionOverride(recordId) {
  return request.post(`/approvals/distribution-overrides/${recordId}/approve`)
}

export function rejectDistributionOverride(recordId) {
  return request.post(`/approvals/distribution-overrides/${recordId}/reject`)
}
