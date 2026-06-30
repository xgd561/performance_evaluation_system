import request from './request'

export function getToReviewList() {
  return request.get('/scores/to-review')
}

export function submitManagerScore(recordId, data) {
  return request.post(`/scores/manager/${recordId}`, data)
}

export function getManagerDraft(recordId) {
  return request.get(`/scores/records/${recordId}/draft`)
}

export function saveManagerDraft(recordId, data) {
  return request.post(`/scores/records/${recordId}/draft`, data)
}

export function deleteManagerDraft(recordId) {
  return request.delete(`/scores/records/${recordId}/draft`)
}

export function getScoreSummary(cycleId, params) {
  return request.get(`/scores/summary/${cycleId}`, { params })
}

export function calculateScores(cycleId) {
  return request.post(`/scores/calculate/${cycleId}`)
}

export function getMyPeerReviews() {
  return request.get('/peer-reviewers/my-reviews')
}

export function submitPeerScore(recordId, data) {
  return request.post(`/scores/peer/${recordId}`, data)
}

export function getMyAssessment() {
  return request.get('/scores/my-assessment')
}

export function getAssessmentDetail(recordId) {
  return request.get(`/scores/records/${recordId}/detail`)
}

export function downloadRecordPdf(recordId) {
  return request.get(`/reports/record/${recordId}/pdf`, {
    responseType: 'blob',
  })
}

export function submitSelfScore(recordId, data) {
  return request.post(`/scores/self/${recordId}`, data)
}
