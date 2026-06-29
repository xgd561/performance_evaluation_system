import request from './request'

export function getPendingApprovals() {
  return request.get('/approvals/pending')
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
