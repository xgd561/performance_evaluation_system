import request from './request'

export function getPendingApprovals(params = {}) {
  return request.get('/approvals/pending', { params })
}

export function getApprovalDetail(recordId) {
  return request.get(`/approvals/${recordId}`)
}

export function getDepartmentDistribution(departmentId) {
  return request.get('/approvals/department-distribution', { params: { department_id: departmentId } })
}

export function approveRecord(recordId, data) {
  return request.post(`/approvals/${recordId}/approve`, data)
}

export function rejectRecord(recordId, data) {
  return request.post(`/approvals/${recordId}/reject`, data)
}

export function rollbackRecord(recordId, data) {
  return request.post(`/approvals/${recordId}/rollback`, data)
}

export function getApprovalHistory(recordId) {
  return request.get('/approvals/history', { params: { record_id: recordId } })
}
