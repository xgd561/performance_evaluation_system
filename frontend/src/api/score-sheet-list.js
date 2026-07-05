import request from './request'

export function getScoreSheetList(params) {
  return request.get('/scores/to-review', { params })
}
