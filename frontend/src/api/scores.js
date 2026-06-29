import request from './request'

export function getToReviewList() {
  return request.get('/scores/to-review')
}

export function submitManagerScore(recordId, data) {
  return request.post(`/scores/manager/${recordId}`, data)
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

export function submitSelfScore(recordId, data) {
  return request.post(`/scores/self/${recordId}`, data)
}
