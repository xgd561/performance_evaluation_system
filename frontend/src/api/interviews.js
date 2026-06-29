import request from './request'

export function getPendingInterviews() {
  return request.get('/interviews/pending')
}

export function createInterview(recordId, data) {
  return request.post(`/interviews/${recordId}`, data)
}

export function getInterview(recordId) {
  return request.get(`/interviews/${recordId}`)
}

export function updateInterview(recordId, data) {
  return request.put(`/interviews/${recordId}`, data)
}

export function getEmployeeInterviewHistory(employeeId) {
  return request.get(`/interviews/employee/${employeeId}`)
}
