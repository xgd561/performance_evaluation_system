import request from './request'

export function getMyAssessment() {
  return request.get('/scores/my-assessment')
}

export function submitSelfScore(recordId, data) {
  return request.post('/scores/self', { record_id: recordId, ...data })
}

export function submitManagerScore(recordId, data) {
  return request.post(`/scores/manager/${recordId}`, data)
}

export function submitPeerScore(recordId, data) {
  return request.post(`/scores/peer/${recordId}`, data)
}

export function getToReviewList(params) {
  return request.get('/scores/to-review', { params })
}

export function getScoreSummary(cycleId) {
  return request.get(`/scores/summary/${cycleId}`)
}

export function triggerCalculate(cycleId) {
  return request.post(`/scores/calculate/${cycleId}`)
}

export function getDraft(recordId) {
  return request.get(`/records/${recordId}/draft`)
}

export function saveDraft(recordId, data) {
  return request.post(`/records/${recordId}/draft`, data)
}
