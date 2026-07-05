import pytest
from app.services.score_calculator import calculate_weighted_score, calculate_kpi_weighted_performance


class MockScoreDetail:
    def __init__(self, weight, self_score=None, manager_score=None):
        self.weight = weight
        self.self_score = self_score
        self.manager_score = manager_score


class TestCalculateWeightedScore:
    """加权计算核心单元测试"""

    def test_basic_calculation(self):
        """基本加权计算：自评(82/84/88) + 上级(85/88/90) + 协作(86)"""
        self_scores = {"performance": 82, "ability": 84, "attitude": 88}
        manager_scores = {"performance": 85, "ability": 88, "attitude": 90}
        peer_scores = {"ability": 86}
        dim_weights = {"performance": 0.5, "ability": 0.3, "attitude": 0.2}
        reviewer_weights = {
            "performance": {"self": 0.3, "manager": 0.7},
            "ability": {"self": 0.3, "manager": 0.5, "peer": 0.2},
            "attitude": {"self": 0.3, "manager": 0.7},
        }

        result = calculate_weighted_score(
            self_scores, manager_scores, peer_scores, dim_weights, reviewer_weights
        )

        # performance = 82*0.3 + 85*0.7 = 84.1
        assert result["weighted_performance"] == 84.1
        # ability = 84*0.3 + 88*0.5 + 86*0.2 = 86.0
        assert result["weighted_ability"] == 86.0
        # attitude = 88*0.3 + 90*0.7 = 89.4
        assert result["weighted_attitude"] == 89.4
        # total = 84.1*0.5 + 86.0*0.3 + 89.4*0.2 = 86.03
        assert result["total_score"] == 86.0

    def test_no_peer_scores(self):
        """无协作评分时，performance 和 attitude 正常计算，ability 仅自评+上级"""
        self_scores = {"performance": 80, "ability": 80, "attitude": 80}
        manager_scores = {"performance": 90, "ability": 90, "attitude": 90}
        peer_scores = {}
        dim_weights = {"performance": 0.5, "ability": 0.3, "attitude": 0.2}
        reviewer_weights = {
            "performance": {"self": 0.3, "manager": 0.7},
            "ability": {"self": 0.3, "manager": 0.5, "peer": 0.2},
            "attitude": {"self": 0.3, "manager": 0.7},
        }

        result = calculate_weighted_score(
            self_scores, manager_scores, peer_scores, dim_weights, reviewer_weights
        )

        # ability 没有 peer，按 self 0.3 + manager 0.5 加权 = 80*0.3 + 90*0.5 = 69 / 0.8 = 86.25
        assert result["weighted_ability"] == 86.25
        # total = 87*0.5 + 86.25*0.3 + 87*0.2 = 86.775
        assert result["total_score"] == 86.8

    def test_precision_rounding(self):
        """精度测试：中间结果保留 2 位小数，总分保留 1 位"""
        self_scores = {"performance": 77.55, "ability": 83.33, "attitude": 91.67}
        manager_scores = {"performance": 82.45, "ability": 88.88, "attitude": 95.00}
        peer_scores = {}
        dim_weights = {"performance": 0.4, "ability": 0.35, "attitude": 0.25}
        reviewer_weights = {
            "performance": {"self": 0.4, "manager": 0.6},
            "ability": {"self": 0.4, "manager": 0.6},
            "attitude": {"self": 0.4, "manager": 0.6},
        }

        result = calculate_weighted_score(
            self_scores, manager_scores, peer_scores, dim_weights, reviewer_weights
        )

        # 各维度保留 2 位小数
        assert result["weighted_performance"] == 80.49
        assert result["weighted_ability"] == 86.66
        assert result["weighted_attitude"] == 93.67
        # 总分保留 1 位
        assert result["total_score"] == 86.5

    def test_kpi_weighted_performance_override(self):
        """KPI 加权 performance 覆盖原始 performance"""
        self_scores = {"performance": 82, "ability": 84, "attitude": 88}
        manager_scores = {"performance": 85, "ability": 88, "attitude": 90}
        peer_scores = {}
        dim_weights = {"performance": 0.5, "ability": 0.3, "attitude": 0.2}
        reviewer_weights = {
            "performance": {"self": 0.3, "manager": 0.7},
            "ability": {"self": 0.3, "manager": 0.7},
            "attitude": {"self": 0.3, "manager": 0.7},
        }

        result = calculate_weighted_score(
            self_scores, manager_scores, peer_scores, dim_weights, reviewer_weights,
            kpi_weighted_self_performance=88.5,
            kpi_weighted_manager_performance=92.0,
        )

        assert result["weighted_performance"] == 90.95
        assert result["total_score"] == 89.1

    def test_empty_scores(self):
        """空评分数据返回 0 分"""
        result = calculate_weighted_score({}, {}, {}, {}, {})
        assert result["weighted_performance"] == 0
        assert result["weighted_ability"] == 0
        assert result["weighted_attitude"] == 0
        assert result["total_score"] == 0

    def test_boundary_values(self):
        """边界值：0 分和 100 分"""
        self_scores = {"performance": 0, "ability": 0, "attitude": 0}
        manager_scores = {"performance": 100, "ability": 100, "attitude": 100}
        peer_scores = {}
        dim_weights = {"performance": 0.5, "ability": 0.3, "attitude": 0.2}
        reviewer_weights = {
            "performance": {"self": 0.3, "manager": 0.7},
            "ability": {"self": 0.3, "manager": 0.7},
            "attitude": {"self": 0.3, "manager": 0.7},
        }

        result = calculate_weighted_score(
            self_scores, manager_scores, peer_scores, dim_weights, reviewer_weights
        )

        assert result["weighted_performance"] == 70.0
        assert result["weighted_ability"] == 70.0
        assert result["weighted_attitude"] == 70.0
        assert result["total_score"] == 70.0


class TestCalculateKpiWeightedPerformance:
    """KPI 加权 performance 计算单元测试"""

    def test_basic_kpi_weighted(self):
        """基本 KPI 加权计算"""
        details = [
            MockScoreDetail(weight=0.4, self_score=80, manager_score=85),
            MockScoreDetail(weight=0.6, self_score=90, manager_score=95),
        ]
        result = calculate_kpi_weighted_performance(details, "self")
        # 80*0.4 + 90*0.6 = 86
        assert result == 86.0

    def test_manager_kpi_weighted(self):
        """上级 KPI 加权计算"""
        details = [
            MockScoreDetail(weight=0.3, self_score=70, manager_score=75),
            MockScoreDetail(weight=0.7, self_score=85, manager_score=90),
        ]
        result = calculate_kpi_weighted_performance(details, "manager")
        # 75*0.3 + 90*0.7 = 85.5
        assert result == 85.5

    def test_no_scores(self):
        """无评分数据返回 None"""
        details = [
            MockScoreDetail(weight=0.5, self_score=None, manager_score=None),
        ]
        result = calculate_kpi_weighted_performance(details, "self")
        assert result is None

    def test_empty_details(self):
        """空明细返回 None"""
        result = calculate_kpi_weighted_performance([], "self")
        assert result is None

    def test_zero_total_weight(self):
        """总权重为 0 返回 None"""
        details = [
            MockScoreDetail(weight=0, self_score=80, manager_score=85),
        ]
        result = calculate_kpi_weighted_performance(details, "self")
        assert result is None
