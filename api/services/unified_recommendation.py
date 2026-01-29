"""
Unified Recommendation Service
Aggregates all signals (Technical, Triple Screen, Multi-Timeframe, Patterns)
and provides ONE clear final recommendation using AI as the final arbiter.
"""
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class RecommendationType(str, Enum):
    STRONG_BUY = "STRONG BUY"
    BUY = "BUY"
    LEAN_BUY = "LEAN BUY"
    HOLD = "HOLD"
    LEAN_SELL = "LEAN SELL"
    SELL = "SELL"
    STRONG_SELL = "STRONG SELL"


@dataclass
class SignalSource:
    """Individual signal from a source"""
    source: str  # e.g., "Triple Screen", "Multi-Timeframe", "Pattern Analysis"
    recommendation: str
    score: float  # 0-100
    weight: float  # How much this source matters (0-1)
    reasoning: str
    bullish_signals: List[str]
    bearish_signals: List[str]


@dataclass
class UnifiedRecommendation:
    """Final unified recommendation"""
    symbol: str
    final_recommendation: str
    confidence: float  # 0-100
    composite_score: float  # Weighted average of all scores
    reasoning: str
    action_summary: str  # One-line actionable advice
    sources: List[SignalSource]
    conflicts: List[str]  # Any conflicting signals
    risk_level: str  # LOW, MEDIUM, HIGH
    suggested_entry: Optional[float]
    suggested_stop_loss: Optional[float]
    suggested_target: Optional[float]


class UnifiedRecommendationService:
    """
    Aggregates signals from multiple analysis systems and produces
    ONE clear, unified recommendation.
    """

    # Weights for different signal sources (must sum to 1.0)
    SOURCE_WEIGHTS = {
        "triple_screen": 0.30,      # Elder's Triple Screen - strong methodology
        "multi_timeframe": 0.25,    # Multi-TF analysis
        "technical": 0.20,          # Basic technical (RSI, MACD, etc.)
        "patterns": 0.15,           # Chart patterns
        "ai_sentiment": 0.10,       # AI analysis/sentiment
    }

    # Recommendation scores (for averaging)
    RECOMMENDATION_SCORES = {
        "STRONG BUY": 95,
        "STRONG_BUY": 95,
        "BUY": 75,
        "LEAN BUY": 60,
        "LEAN_BUY": 60,
        "HOLD": 50,
        "WAIT": 50,
        "LEAN SELL": 40,
        "LEAN_SELL": 40,
        "SELL": 25,
        "STRONG SELL": 5,
        "STRONG_SELL": 5,
    }

    def __init__(self):
        pass

    def _normalize_recommendation(self, rec: str) -> str:
        """Normalize recommendation string"""
        if not rec:
            return "HOLD"
        rec = rec.upper().replace("_", " ").strip()
        # Map variations
        mapping = {
            "STRONG BUY": "STRONG BUY",
            "STRONGBUY": "STRONG BUY",
            "BUY": "BUY",
            "LEAN BUY": "LEAN BUY",
            "LEANBUY": "LEAN BUY",
            "HOLD": "HOLD",
            "WAIT": "HOLD",
            "NEUTRAL": "HOLD",
            "LEAN SELL": "LEAN SELL",
            "LEANSELL": "LEAN SELL",
            "SELL": "SELL",
            "STRONG SELL": "STRONG SELL",
            "STRONGSELL": "STRONG SELL",
            "WATCH": "HOLD",
        }
        return mapping.get(rec, "HOLD")

    def _score_to_recommendation(self, score: float) -> str:
        """Convert a score (0-100) to a recommendation"""
        if score >= 85:
            return "STRONG BUY"
        elif score >= 70:
            return "BUY"
        elif score >= 58:
            return "LEAN BUY"
        elif score >= 42:
            return "HOLD"
        elif score >= 30:
            return "LEAN SELL"
        elif score >= 15:
            return "SELL"
        else:
            return "STRONG SELL"

    def _recommendation_to_score(self, rec: str) -> float:
        """Convert recommendation to numeric score"""
        normalized = self._normalize_recommendation(rec)
        return self.RECOMMENDATION_SCORES.get(normalized, 50)

    def _calculate_risk_level(self, sources: List[SignalSource], conflicts: List[str]) -> str:
        """Determine risk level based on signal agreement"""
        if len(conflicts) >= 3:
            return "HIGH"
        elif len(conflicts) >= 1:
            return "MEDIUM"

        # Check score variance
        scores = [s.score for s in sources if s.score > 0]
        if scores:
            variance = max(scores) - min(scores)
            if variance > 40:
                return "HIGH"
            elif variance > 20:
                return "MEDIUM"

        return "LOW"

    def aggregate_signals(
        self,
        symbol: str,
        triple_screen_data: Optional[Dict] = None,
        multi_timeframe_data: Optional[Dict] = None,
        technical_data: Optional[Dict] = None,
        pattern_data: Optional[Dict] = None,
        ai_analysis_data: Optional[Dict] = None,
        current_price: Optional[float] = None,
    ) -> UnifiedRecommendation:
        """
        Aggregate all signal sources into one unified recommendation.
        """
        sources: List[SignalSource] = []
        conflicts: List[str] = []

        # Process Triple Screen
        if triple_screen_data:
            ts_rec = triple_screen_data.get("recommendation", "HOLD")
            ts_alignment = triple_screen_data.get("alignment", 50)
            ts_score = ts_alignment  # Use alignment as score

            bullish = []
            bearish = []
            for screen in ["tide", "wave", "ripple"]:
                screen_data = triple_screen_data.get(screen, {})
                if screen_data.get("direction") == "bullish":
                    bullish.append(f"{screen.title()} bullish")
                elif screen_data.get("direction") == "bearish":
                    bearish.append(f"{screen.title()} bearish")

            sources.append(SignalSource(
                source="Triple Screen",
                recommendation=self._normalize_recommendation(ts_rec),
                score=ts_score,
                weight=self.SOURCE_WEIGHTS["triple_screen"],
                reasoning=triple_screen_data.get("description", ""),
                bullish_signals=bullish,
                bearish_signals=bearish,
            ))

        # Process Multi-Timeframe
        if multi_timeframe_data:
            mtf_rec = multi_timeframe_data.get("overall_recommendation", "HOLD")
            mtf_score = multi_timeframe_data.get("overall_score", 50)

            bullish = []
            bearish = []
            timeframes = multi_timeframe_data.get("timeframes", {})
            for tf_name, tf_data in timeframes.items():
                tf_rec = tf_data.get("recommendation", "HOLD")
                if "BUY" in tf_rec.upper():
                    bullish.append(f"{tf_name}: {tf_rec}")
                elif "SELL" in tf_rec.upper():
                    bearish.append(f"{tf_name}: {tf_rec}")

            sources.append(SignalSource(
                source="Multi-Timeframe",
                recommendation=self._normalize_recommendation(mtf_rec),
                score=mtf_score,
                weight=self.SOURCE_WEIGHTS["multi_timeframe"],
                reasoning=f"Score: {mtf_score}/100",
                bullish_signals=bullish,
                bearish_signals=bearish,
            ))

        # Process Technical Indicators
        if technical_data:
            tech_score = technical_data.get("score", 50)
            tech_rec = technical_data.get("recommendation", "HOLD")

            bullish = []
            bearish = []
            signals = technical_data.get("signals", [])
            for sig in signals:
                sig_lower = sig.lower()
                if "bullish" in sig_lower or "above" in sig_lower or "up" in sig_lower:
                    bullish.append(sig)
                elif "bearish" in sig_lower or "below" in sig_lower or "down" in sig_lower:
                    bearish.append(sig)

            sources.append(SignalSource(
                source="Technical",
                recommendation=self._normalize_recommendation(tech_rec),
                score=tech_score,
                weight=self.SOURCE_WEIGHTS["technical"],
                reasoning=f"RSI: {technical_data.get('indicators', {}).get('rsi', 'N/A')}",
                bullish_signals=bullish[:3],
                bearish_signals=bearish[:3],
            ))

        # Process Pattern Analysis
        if pattern_data:
            patterns = pattern_data.get("patterns", [])
            bullish_score = pattern_data.get("bullish_score", 0)
            bearish_score = pattern_data.get("bearish_score", 0)

            # Calculate pattern score
            if bullish_score + bearish_score > 0:
                pattern_score = 50 + (bullish_score - bearish_score) / 2
            else:
                pattern_score = 50

            pattern_rec = pattern_data.get("bias", "neutral")
            if pattern_rec == "bullish":
                pattern_rec = "LEAN BUY"
            elif pattern_rec == "bearish":
                pattern_rec = "LEAN SELL"
            else:
                pattern_rec = "HOLD"

            bullish = [p.get("type", "") for p in patterns if p.get("direction") == "bullish"]
            bearish = [p.get("type", "") for p in patterns if p.get("direction") == "bearish"]

            sources.append(SignalSource(
                source="Patterns",
                recommendation=self._normalize_recommendation(pattern_rec),
                score=pattern_score,
                weight=self.SOURCE_WEIGHTS["patterns"],
                reasoning=f"{len(patterns)} patterns detected",
                bullish_signals=bullish[:3],
                bearish_signals=bearish[:3],
            ))

        # Process AI Analysis
        if ai_analysis_data:
            ai_decision = ai_analysis_data.get("decision", "WAIT")
            ai_reason = ai_analysis_data.get("reason", "")

            # AI decision scoring
            ai_score = 50
            if ai_decision == "APPROVE":
                ai_score = 75
            elif ai_decision == "REJECT":
                ai_score = 25

            sources.append(SignalSource(
                source="AI Sentiment",
                recommendation="BUY" if ai_decision == "APPROVE" else ("SELL" if ai_decision == "REJECT" else "HOLD"),
                score=ai_score,
                weight=self.SOURCE_WEIGHTS["ai_sentiment"],
                reasoning=ai_reason[:100] if ai_reason else "",
                bullish_signals=["AI Approved"] if ai_decision == "APPROVE" else [],
                bearish_signals=["AI Rejected"] if ai_decision == "REJECT" else [],
            ))

        # If no sources, return HOLD
        if not sources:
            return UnifiedRecommendation(
                symbol=symbol,
                final_recommendation="HOLD",
                confidence=0,
                composite_score=50,
                reasoning="No analysis data available",
                action_summary="Wait for more data before taking action",
                sources=[],
                conflicts=[],
                risk_level="HIGH",
                suggested_entry=None,
                suggested_stop_loss=None,
                suggested_target=None,
            )

        # Calculate weighted composite score
        total_weight = sum(s.weight for s in sources)
        composite_score = sum(s.score * s.weight for s in sources) / total_weight if total_weight > 0 else 50

        # Detect conflicts
        recommendations = [s.recommendation for s in sources]
        buy_signals = sum(1 for r in recommendations if "BUY" in r)
        sell_signals = sum(1 for r in recommendations if "SELL" in r)
        hold_signals = sum(1 for r in recommendations if r == "HOLD")

        if buy_signals > 0 and sell_signals > 0:
            conflicts.append(f"Mixed signals: {buy_signals} bullish vs {sell_signals} bearish sources")

        # Check for specific source conflicts
        for i, s1 in enumerate(sources):
            for s2 in sources[i+1:]:
                score_diff = abs(s1.score - s2.score)
                if score_diff > 30:
                    conflicts.append(f"{s1.source} ({s1.recommendation}) conflicts with {s2.source} ({s2.recommendation})")

        # Determine final recommendation from composite score
        final_rec = self._score_to_recommendation(composite_score)

        # Adjust confidence based on agreement
        base_confidence = min(composite_score, 100 - composite_score) * 2  # Higher when more extreme
        agreement_bonus = (1 - len(conflicts) * 0.15) * 20  # Bonus for agreement
        confidence = min(max(base_confidence + agreement_bonus, 20), 95)

        # Determine risk level
        risk_level = self._calculate_risk_level(sources, conflicts)

        # Build reasoning
        reasoning_parts = []
        for s in sorted(sources, key=lambda x: x.weight, reverse=True):
            reasoning_parts.append(f"{s.source}: {s.recommendation} ({s.score:.0f}%)")
        reasoning = " | ".join(reasoning_parts)

        # Build action summary
        if final_rec in ["STRONG BUY", "BUY"]:
            action_summary = f"Consider buying {symbol}. {len([s for s in sources if 'BUY' in s.recommendation])}/{len(sources)} sources bullish."
        elif final_rec in ["STRONG SELL", "SELL"]:
            action_summary = f"Consider selling {symbol}. {len([s for s in sources if 'SELL' in s.recommendation])}/{len(sources)} sources bearish."
        elif final_rec == "LEAN BUY":
            action_summary = f"Slight bullish bias for {symbol}. Wait for confirmation or scale in small."
        elif final_rec == "LEAN SELL":
            action_summary = f"Slight bearish bias for {symbol}. Consider reducing position or waiting."
        else:
            action_summary = f"No clear direction for {symbol}. Wait for stronger signals."

        if conflicts:
            action_summary += f" Note: {len(conflicts)} conflicting signal(s)."

        # Calculate suggested levels from pattern data
        suggested_entry = current_price
        suggested_stop_loss = None
        suggested_target = None

        if pattern_data:
            patterns = pattern_data.get("patterns", [])
            for p in patterns:
                if p.get("stop_loss"):
                    suggested_stop_loss = p.get("stop_loss")
                if p.get("price_target"):
                    suggested_target = p.get("price_target")
                break  # Use first pattern's levels

        return UnifiedRecommendation(
            symbol=symbol,
            final_recommendation=final_rec,
            confidence=confidence,
            composite_score=composite_score,
            reasoning=reasoning,
            action_summary=action_summary,
            sources=sources,
            conflicts=conflicts,
            risk_level=risk_level,
            suggested_entry=suggested_entry,
            suggested_stop_loss=suggested_stop_loss,
            suggested_target=suggested_target,
        )


# Singleton instance
_unified_service: Optional[UnifiedRecommendationService] = None


def get_unified_recommendation_service() -> UnifiedRecommendationService:
    global _unified_service
    if _unified_service is None:
        _unified_service = UnifiedRecommendationService()
    return _unified_service
