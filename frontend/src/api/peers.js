import request from './request'

export function listPeersByCycle(cycleId) {
  return request.get(`/peer-reviewers/cycle/${cycleId}`)
}

export function assignPeer(data) {
  return request.post('/peer-reviewers', data)
}

export function removePeer(relationId) {
  return request.delete(`/peer-reviewers/${relationId}`)
}
