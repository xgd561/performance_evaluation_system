from typing import Dict, Any, Optional


def calculate_weighted_score(
    self_scores: Dict[str, float],
    manager_scores: Dict[str, float],
    peer_scores: Dict[str, float],
    dim_weights: Dict[str, float],
    reviewer_weights: Dict[str, Any],
    kpi_weighted_self_performance: Optional[float] = None,
    kpi_weighted_manager_performance: Optional[float] = None,
) -> Dict[str, Any]:
    """
    计算加权总分和各维度得分。

    按 PRD 4.4.2 公式：
    1. 维度得分 = Σ(评分人维度分 × 评分人维度权重)
    2. 总分 = Σ(维度得分 × 维度权重)
    3. 中间结果保留 2 位小数，最终总分保留 1 位

    Args:
        self_scores: 自评分数 {performance: 82, ability: 84, attitude: 88}
        manager_scores: 上级评分 {performance: 85, ability: 88, attitude: 90}
        peer_scores: 协作评分 {ability: 86}
        dim_weights: 维度权重 {performance: 0.5, ability: 0.3, attitude: 0.2}
        reviewer_weights: 评分人权重 {performance: {self: 0.3, manager: 0.7}, ...}
        kpi_weighted_self_performance: KPI 加权后的自评 performance（如有）
        kpi_weighted_manager_performance: KPI 加权后的上级 performance（如有）

    Returns:
        {
            "weighted_performance": float,
            "weighted_ability": float,
            "weighted_attitude": float,
            "total_score": float,
        }
    """
    adjusted_self = dict(self_scores) if self_scores else {}
    adjusted_manager = dict(manager_scores) if manager_scores else {}

    if kpi_weighted_self_performance is not None:
        adjusted_self["performance"] = kpi_weighted_self_performance
    if kpi_weighted_manager_performance is not None:
        adjusted_manager["performance"] = kpi_weighted_manager_performance

    weighted_dims = {}
    for dim, dim_weight in dim_weights.items():
        scores = {
            "self": adjusted_self.get(dim),
            "manager": adjusted_manager.get(dim),
            "peer": peer_scores.get(dim) if peer_scores else None,
        }

        rw = reviewer_weights.get(dim, reviewer_weights)
        if not rw and any(r in reviewer_weights for r in ["self", "manager", "peer"]):
            rw = reviewer_weights

        total_w = 0.0
        weighted_sum = 0.0
        for reviewer, score in scores.items():
            if score is not None and reviewer in rw:
                weighted_sum += score * rw[reviewer]
                total_w += rw[reviewer]

        if total_w > 0:
            weighted_sum = weighted_sum / total_w

        # 中间结果保留 2 位小数
        weighted_dims[dim] = round(weighted_sum, 2)

    dim_weight_factor = 100.0 if sum(dim_weights.values()) > 1 else 1.0
    total = sum(
        weighted_dims.get(d, 0) * (dim_weights.get(d, 0) / dim_weight_factor)
        for d in dim_weights
    )
    # 最终总分保留 1 位小数
    total = round(total, 1)

    return {
        "weighted_performance": weighted_dims.get("performance", 0),
        "weighted_ability": weighted_dims.get("ability", 0),
        "weighted_attitude": weighted_dims.get("attitude", 0),
        "total_score": total,
    }


def calculate_kpi_weighted_performance(
    score_details: list,
    score_type: str = "self",
) -> Optional[float]:
    """
    根据 KPI 评分明细计算加权 performance 得分。

    Args:
        score_details: ScoreDetail 对象列表，每个对象含 weight, self_score, manager_score
        score_type: 'self' 或 'manager'

    Returns:
        加权 performance 得分，或 None（没有评分数据）
    """
    if not score_details:
        return None

    total_weight = 0.0
    weighted_sum = 0.0
    has_score = False

    for d in score_details:
        if score_type == "self":
            score = d.self_score
        elif score_type == "manager":
            score = d.manager_score
        else:
            score = None

        if score is not None:
            weight = float(d.weight or 0)
            weighted_sum += float(score) * weight
            total_weight += weight
            has_score = True

    if not has_score or total_weight == 0:
        return None

    return round(weighted_sum / total_weight, 1)
