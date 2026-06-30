import request from './request'

export function requestKpiAdjustment(recordId, data) {
  return request.post(`/kpi-templates/${recordId}/adjust`, data)
}

export function getPendingKpiAdjustments() {
  return request.get('/kpi-templates/kpi-adjustments/pending')
}

export function approveKpiAdjustment(adjId) {
  return request.post(`/kpi-templates/kpi-adjustments/${adjId}/approve`)
}

export function rejectKpiAdjustment(adjId) {
  return request.post(`/kpi-templates/kpi-adjustments/${adjId}/reject`)
}
