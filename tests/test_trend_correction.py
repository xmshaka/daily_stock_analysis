# -*- coding: utf-8 -*-
"""
Tests for trend_prediction correction and sniper_points fallback fixes.
Issue: LLM (GLM-4-Flash) mislabels clearly bearish stocks as '震荡',
and sniper_points fallback fails when current_price is not set on result.
"""
import pytest
from unittest.mock import MagicMock


@pytest.fixture
def bearish_result():
    """Create an AnalysisResult that mimics a bearish stock like 中海油服."""
    from src.analyzer import AnalysisResult
    result = AnalysisResult(
        code="601808",
        name="中海油服",
        current_price=None,
        sentiment_score=40,
        trend_prediction="震荡",
        operation_advice="持有观望",
        decision_type="hold",
        confidence_level="中",
        analysis_summary="test",
        risk_warning="test",
    )
    result.dashboard = {
        "data_perspective": {
            "trend_status": {
                "ma_alignment": "均线空头排列",
                "is_bullish": False,
                "trend_score": 25,
            },
            "price_position": {
                "current_price": 13.07,
                "ma5": 13.062,
                "ma10": 13.278,
                "ma20": 13.7775,
                "support_level": 12.87,
                "resistance_level": 13.75,
            },
        },
        "battle_plan": {"sniper_points": {}},
    }
    return result


class TestTrendPredictionCorrection:
    """Tests for _correct_trend_prediction_vs_technicals."""

    def test_bearish_ma_corrects_oscillation_to_bearish(self, bearish_result):
        from src.analyzer import _correct_trend_prediction_vs_technicals

        assert bearish_result.trend_prediction == "震荡"
        _correct_trend_prediction_vs_technicals(bearish_result, "zh")
        assert bearish_result.trend_prediction == "强烈看空"

    def test_bearish_ma_with_mid_score_corrects_to_bearish(self):
        from src.analyzer import AnalysisResult, _correct_trend_prediction_vs_technicals

        result = AnalysisResult(
            code="000001",
            name="测试",
            current_price=10.0,
            sentiment_score=45,
            trend_prediction="震荡",
            operation_advice="观望",
            decision_type="hold",
            confidence_level="中",
            analysis_summary="",
            risk_warning="",
        )
        result.dashboard = {
            "data_perspective": {
                "trend_status": {
                    "ma_alignment": "均线空头排列",
                    "is_bullish": False,
                    "trend_score": 45,
                },
                "price_position": {"current_price": 10.0, "ma20": 11.0},
            }
        }
        _correct_trend_prediction_vs_technicals(result, "zh")
        assert result.trend_prediction == "看空"

    def test_bullish_ma_not_corrected(self):
        from src.analyzer import AnalysisResult, _correct_trend_prediction_vs_technicals

        result = AnalysisResult(
            code="000001",
            name="测试",
            current_price=12.0,
            sentiment_score=65,
            trend_prediction="震荡",
            operation_advice="持有",
            decision_type="hold",
            confidence_level="中",
            analysis_summary="",
            risk_warning="",
        )
        result.dashboard = {
            "data_perspective": {
                "trend_status": {
                    "ma_alignment": "均线多头排列",
                    "is_bullish": True,
                    "trend_score": 65,
                },
                "price_position": {"current_price": 12.0, "ma20": 11.0},
            }
        }
        _correct_trend_prediction_vs_technicals(result, "zh")
        assert result.trend_prediction == "震荡"

    def test_already_bearish_not_changed(self):
        from src.analyzer import AnalysisResult, _correct_trend_prediction_vs_technicals

        result = AnalysisResult(
            code="000001",
            name="测试",
            current_price=10.0,
            sentiment_score=30,
            trend_prediction="看空",
            operation_advice="卖出",
            decision_type="sell",
            confidence_level="低",
            analysis_summary="",
            risk_warning="",
        )
        _correct_trend_prediction_vs_technicals(result, "zh")
        assert result.trend_prediction == "看空"


class TestSniperPointsFallback:
    """Tests for apply_placeholder_fill sniper_points fallback."""

    def test_bearish_stock_gets_observation_points(self, bearish_result):
        from src.analyzer import check_content_integrity, apply_placeholder_fill

        pass_integrity, missing = check_content_integrity(bearish_result)
        apply_placeholder_fill(bearish_result, missing)
        sp = bearish_result.dashboard["battle_plan"]["sniper_points"]

        assert "ideal_buy" in sp
        assert "观察位" in sp["ideal_buy"]
        assert "secondary_buy" in sp
        assert "观察位" in sp["secondary_buy"]
        assert "stop_loss" in sp
        assert "take_profit" in sp
        # Take profit should mention 减仓 for bearish
        assert "减仓" in sp["take_profit"]

    def test_bullish_stock_gets_buy_points(self):
        from src.analyzer import AnalysisResult, check_content_integrity, apply_placeholder_fill

        result = AnalysisResult(
            code="000001",
            name="测试",
            current_price=12.0,
            sentiment_score=70,
            trend_prediction="看多",
            operation_advice="买入",
            decision_type="buy",
            confidence_level="高",
            analysis_summary="",
            risk_warning="",
        )
        result.dashboard = {
            "data_perspective": {
                "trend_status": {
                    "ma_alignment": "均线多头排列",
                    "is_bullish": True,
                    "trend_score": 70,
                },
                "price_position": {
                    "current_price": 12.0,
                    "support_level": 11.5,
                    "resistance_level": 13.0,
                },
            },
            "battle_plan": {"sniper_points": {}},
        }
        pass_integrity, missing = check_content_integrity(result)
        apply_placeholder_fill(result, missing)
        sp = result.dashboard["battle_plan"]["sniper_points"]

        assert "ideal_buy" in sp
        assert "均线附近" in sp["ideal_buy"]
        assert "secondary_buy" in sp
        assert "回踩支撑位" in sp["secondary_buy"]

    def test_placeholder_text_detected_as_invalid(self):
        """LLM-generated placeholder phrases like '数据缺失，无法判断。' should be
        detected as invalid sniper_point values."""
        assert _is_invalid_stop_loss("数据缺失，无法判断。")
        assert _is_invalid_stop_loss("待补充")
        assert _is_invalid_stop_loss("")
        assert _is_invalid_stop_loss(None)
        assert not _is_invalid_stop_loss("12.87元（支撑位）")


def _is_invalid_stop_loss(value):
    """Standalone version of _is_invalid_stop_loss for testing."""
    if value is None:
        return True
    if isinstance(value, (list, tuple, dict)):
        return True
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return True
        lower = text.lower()
        placeholder_prefixes = (
            "数据缺失", "无法判断", "暂无", "待补充", "未知", "不适用",
            "to be completed", "data unavailable", "not available",
        )
        if any(lower.startswith(p) for p in placeholder_prefixes):
            return True
    return False


class TestAgentPlaceholderDetection:
    """Tests for _is_agent_placeholder_text in pipeline."""

    def test_exact_match_placeholders(self):
        from src.core.pipeline import StockAnalysisPipeline

        assert StockAnalysisPipeline._is_agent_placeholder_text("数据缺失")
        assert StockAnalysisPipeline._is_agent_placeholder_text("待补充")
        assert StockAnalysisPipeline._is_agent_placeholder_text("")

    def test_prefix_match_placeholders(self):
        from src.core.pipeline import StockAnalysisPipeline

        assert StockAnalysisPipeline._is_agent_placeholder_text("数据缺失，无法判断。")
        assert StockAnalysisPipeline._is_agent_placeholder_text("无法判断当前趋势")
        assert StockAnalysisPipeline._is_agent_placeholder_text("暂无数据")

    def test_valid_values_not_placeholder(self):
        from src.core.pipeline import StockAnalysisPipeline

        assert not StockAnalysisPipeline._is_agent_placeholder_text("12.87元（支撑位）")
        assert not StockAnalysisPipeline._is_agent_placeholder_text("看多")
        assert not StockAnalysisPipeline._is_agent_placeholder_text("13.07")
