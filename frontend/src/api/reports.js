import request from './request'

export function getDistribution(cycleId) {
  return request.get(`/reports/cycle/${cycleId}/distribution`)
}

export function exportCycleReport(cycleId) {
  return request.get(`/reports/cycle/${cycleId}/export`)
}

export function getEmployeeTrend(employeeId) {
  return request.get(`/reports/employee/${employeeId}/trend`)
}
