/**
 * 评分锚点常量
 * 前后端需保持一致，修改时同步更新 backend/app/core/constants.py
 */
export const SCORING_ANCHORS = [
  { range: '90-100', label: '优秀', desc: '超出预期，表现卓越' },
  { range: '80-89', label: '良好', desc: '符合预期，表现稳定' },
  { range: '60-79', label: '合格', desc: '基本符合，仍有提升空间' },
  { range: '0-59', label: '待改进', desc: '表现不足，需要制定改进计划' },
];
