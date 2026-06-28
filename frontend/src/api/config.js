import request from './request'

export function getGradeRules() {
  return request.get('/config/grade-rules')
}

export function updateGradeRules(data) {
  return request.put('/config/grade-rules', data)
}

export function getDimensionWeights() {
  return request.get('/config/dimension-weights')
}

export function updateDimensionWeights(data) {
  return request.put('/config/dimension-weights', data)
}

export function getReviewerWeights() {
  return request.get('/config/reviewer-weights')
}

export function updateReviewerWeights(data) {
  return request.put('/config/reviewer-weights', data)
}

export function getSmallDeptExemption() {
  return request.get('/config/small-dept-exemption')
}

export function updateSmallDeptExemption(data) {
  return request.put('/config/small-dept-exemption', data)
}
