import json
from collections import Counter
from typing import List, Dict, Any


def _get_next_lower_grade(grade: str) -> str:
    mapping = {"A": "B", "B": "C", "C": "D", "D": "D"}
    return mapping.get(grade, "D")


def _small_dept_caps(dept_size: int) -> Dict[str, int]:
    if dept_size <= 1:
        return {"A": 1, "B": 1, "C": 1, "D": 1}
    elif dept_size <= 3:
        return {"A": 1, "B": 100, "C": 100, "D": 1}
    else:
        return {"A": 1, "B": 100, "C": 100, "D": 1}


def _map_grade(total_score: float, grade_rules: Dict[str, Any]) -> str:
    for grade, rule in grade_rules.items():
        if isinstance(rule, dict):
            mn = rule.get("min", 0)
            mx = rule.get("max", 100)
            if mn <= total_score <= mx:
                return grade
    return "D"


def enforce_distribution(
    records: List[Any],
    grade_rules: Dict[str, Any],
    dept_size: int,
    small_dept_exemption: bool = True,
) -> Dict[str, Any]:
    """
    按部门强制分布规则校验并调整等级。

    Args:
        records: 该部门的考核记录列表（已计算 total_score）
        grade_rules: 考核周期的等级规则，如 {"A": {"min": 90, "max": 100, "ratio_limit": 0.2}, ...}
        dept_size: 部门参与考核的人数
        small_dept_exemption: 是否启用小部门豁免

    Returns:
        {
            "adjusted_records": 调整后的记录列表,
            "adjustment_log": 调整日志列表,
            "override_candidates": 特批候选人列表,
            "is_compliant": 是否合规,
            "final_counts": 最终等级分布,
        }
    """
    # 1. 按总分从高到低排序
    sorted_records = sorted(records, key=lambda r: float(r.total_score or 0), reverse=True)

    # 2. 计算各等级人数上限
    if small_dept_exemption and dept_size <= 5:
        caps = _small_dept_caps(dept_size)
    else:
        caps = {}
        for grade, rule in grade_rules.items():
            if isinstance(rule, dict):
                ratio_limit = rule.get("ratio_limit")
                if ratio_limit is not None:
                    caps[grade] = int(dept_size * ratio_limit)
                else:
                    caps[grade] = dept_size
            else:
                caps[grade] = dept_size

    # 3. 首次映射等级（基于分数区间）
    for r in sorted_records:
        r.original_grade = _map_grade(float(r.total_score or 0), grade_rules)
        r.grade = r.original_grade

    # 4. 校验并调整
    adjustment_log = []
    max_iterations = 10  # 防止无限循环

    for _ in range(max_iterations):
        grade_counts = Counter(r.grade for r in sorted_records)
        overflow = {
            g: max(0, grade_counts.get(g, 0) - caps.get(g, 0))
            for g in caps
        }

        if all(v == 0 for v in overflow.values()):
            break

        # 从 A → B → C 依次处理超限
        for grade in ["A", "B", "C"]:
            if overflow.get(grade, 0) > 0:
                candidates = [r for r in sorted_records if r.grade == grade]
                # 按分数由低到高排序（降级低分者）
                candidates.sort(key=lambda r: float(r.total_score or 0))
                for i in range(overflow[grade]):
                    if i < len(candidates):
                        record = candidates[i]
                        next_grade = _get_next_lower_grade(grade)
                        old_grade = record.grade
                        record.grade = next_grade
                        adjustment_log.append({
                            "employee_id": record.employee_id,
                            "total_score": float(record.total_score or 0),
                            "from_grade": old_grade,
                            "to_grade": next_grade,
                            "reason": f"因{grade}等级超限（上限{caps[grade]}人），系统自动降级",
                        })

    # 5. 标记特批候选人：被从 A 强制降级且总分仍 ≥ 90
    override_candidates = [
        log for log in adjustment_log
        if log["from_grade"] == "A" and log["total_score"] >= 90
    ]

    final_counts = Counter(r.grade for r in sorted_records)
    is_compliant = all(
        final_counts.get(g, 0) <= caps.get(g, 0) for g in caps
    )

    return {
        "adjusted_records": sorted_records,
        "adjustment_log": adjustment_log,
        "override_candidates": override_candidates,
        "is_compliant": is_compliant,
        "final_counts": dict(final_counts),
    }
