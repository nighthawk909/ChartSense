"""
Post-Mortem Trade Analysis Service

Analyzes completed trades to generate insights about what went well,
what could have been done better, and lessons learned.
"""
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json

from database.connection import SessionLocal
from database.models import Trade
from services.alpha_vantage import AlphaVantageService
from services.indicators import IndicatorService


class PostMortemService:
    """
    Service for analyzing completed trades and generating insights.
    Uses AI to provide human-readable explanations of trade outcomes.
    """

    def __init__(self):
        self.av_service = AlphaVantageService()
        self.indicator_service = IndicatorService()
        self.openai_client = None
        self._init_openai()

    def _init_openai(self):
        """Initialize OpenAI client if API key is available."""
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            try:
                from openai import OpenAI
                self.openai_client = OpenAI(api_key=api_key)
            except ImportError:
                pass

    async def analyze_trade(self, trade_id: int) -> Dict[str, Any]:
        """
        Perform comprehensive post-mortem analysis on a completed trade.

        Returns analysis including:
        - Trade summary
        - What went well / What went wrong
        - Optimal exit analysis
        - Lessons learned
        - AI-generated explanation
        """
        db = SessionLocal()
        try:
            trade = db.query(Trade).filter(Trade.id == trade_id).first()
            if not trade:
                return {"error": f"Trade {trade_id} not found"}

            if not trade.exit_time:
                return {"error": "Trade is still open - cannot analyze"}

            # Build analysis
            analysis = await self._build_analysis(trade)

            # Save analysis to database
            trade.post_mortem_analysis = analysis
            trade.analyzed_at = datetime.now()

            if analysis.get("could_have_done_better") is not None:
                trade.could_have_done_better = analysis["could_have_done_better"]
            if analysis.get("optimal_exit_price"):
                trade.optimal_exit_price = analysis["optimal_exit_price"]
            if analysis.get("missed_profit"):
                trade.missed_profit = analysis["missed_profit"]
            if analysis.get("lessons_learned"):
                trade.lessons_learned = analysis["lessons_learned"][:1000]

            db.commit()

            return analysis
        finally:
            db.close()

    async def _build_analysis(self, trade: Trade) -> Dict[str, Any]:
        """Build the complete analysis for a trade."""
        analysis = {
            "trade_id": trade.id,
            "symbol": trade.symbol,
            "analyzed_at": datetime.now().isoformat(),
        }

        # 1. Basic trade metrics
        analysis["trade_summary"] = self._get_trade_summary(trade)

        # 2. Get price history around the trade
        price_data = await self._get_price_history_around_trade(trade)
        if price_data:
            analysis["price_context"] = price_data

        # 3. Calculate optimal exit
        optimal = self._calculate_optimal_exit(trade, price_data)
        analysis.update(optimal)

        # 4. Analyze what went well/wrong
        analysis["what_went_well"] = self._analyze_positives(trade, optimal)
        analysis["what_went_wrong"] = self._analyze_negatives(trade, optimal)

        # 5. Generate lessons learned
        analysis["lessons_learned"] = self._generate_lessons(trade, optimal)

        # 6. AI-generated summary
        if self.openai_client:
            ai_summary = await self._generate_ai_summary(trade, analysis)
            analysis["ai_summary"] = ai_summary

        return analysis

    def _get_trade_summary(self, trade: Trade) -> Dict[str, Any]:
        """Generate basic trade metrics summary."""
        duration = None
        if trade.entry_time and trade.exit_time:
            delta = trade.exit_time - trade.entry_time
            duration = {
                "hours": delta.total_seconds() / 3600,
                "days": delta.days,
                "formatted": self._format_duration(delta)
            }

        return {
            "entry_price": trade.entry_price,
            "exit_price": trade.exit_price,
            "quantity": trade.quantity,
            "side": trade.side,
            "entry_time": trade.entry_time.isoformat() if trade.entry_time else None,
            "exit_time": trade.exit_time.isoformat() if trade.exit_time else None,
            "duration": duration,
            "profit_loss": trade.profit_loss,
            "profit_loss_pct": trade.profit_loss_pct,
            "exit_reason": trade.exit_reason,
            "trade_type": trade.trade_type,
            "entry_score": trade.entry_score,
            "was_profitable": (trade.profit_loss or 0) > 0,
        }

    async def _get_price_history_around_trade(self, trade: Trade) -> Optional[Dict]:
        """Get price history around the trade period."""
        try:
            # Get daily history
            history = await self.av_service.get_history(trade.symbol)
            if not history:
                return None

            # Find relevant period
            entry_date = trade.entry_time.date() if trade.entry_time else None
            exit_date = trade.exit_time.date() if trade.exit_time else None

            if not entry_date or not exit_date:
                return None

            # Get prices during trade period and some context before/after
            # Extend window by 5 days before and after
            start_date = entry_date - timedelta(days=10)
            end_date = exit_date + timedelta(days=5)

            filtered_dates = []
            filtered_prices = []
            filtered_highs = []
            filtered_lows = []

            for i, date in enumerate(history.dates):
                if isinstance(date, str):
                    d = datetime.fromisoformat(date).date()
                else:
                    d = date.date() if hasattr(date, 'date') else date

                if start_date <= d <= end_date:
                    filtered_dates.append(date)
                    filtered_prices.append(history.prices[i] if i < len(history.prices) else None)
                    filtered_highs.append(history.highs[i] if i < len(history.highs) else None)
                    filtered_lows.append(history.lows[i] if i < len(history.lows) else None)

            if not filtered_prices:
                return None

            # Find max/min during trade period
            trade_period_prices = []
            trade_period_highs = []
            trade_period_lows = []

            for i, date in enumerate(filtered_dates):
                if isinstance(date, str):
                    d = datetime.fromisoformat(date).date()
                else:
                    d = date.date() if hasattr(date, 'date') else date

                if entry_date <= d <= exit_date:
                    if filtered_prices[i]:
                        trade_period_prices.append(filtered_prices[i])
                    if filtered_highs[i]:
                        trade_period_highs.append(filtered_highs[i])
                    if filtered_lows[i]:
                        trade_period_lows.append(filtered_lows[i])

            max_price = max(trade_period_highs) if trade_period_highs else None
            min_price = min(trade_period_lows) if trade_period_lows else None

            return {
                "dates": [str(d) for d in filtered_dates],
                "prices": filtered_prices,
                "highs": filtered_highs,
                "lows": filtered_lows,
                "max_price_during_trade": max_price,
                "min_price_during_trade": min_price,
            }
        except Exception as e:
            return {"error": str(e)}

    def _calculate_optimal_exit(self, trade: Trade, price_data: Optional[Dict]) -> Dict:
        """Calculate what the optimal exit would have been."""
        result = {
            "optimal_exit_price": None,
            "missed_profit": None,
            "could_have_done_better": None,
            "optimal_exit_analysis": None,
        }

        if not price_data or "error" in price_data:
            return result

        max_price = price_data.get("max_price_during_trade")
        min_price = price_data.get("min_price_during_trade")

        if not max_price or not min_price:
            return result

        actual_exit = trade.exit_price or 0
        entry = trade.entry_price or 0
        quantity = trade.quantity or 0
        is_long = trade.side == "BUY"

        if is_long:
            # For long positions, optimal exit would be at max price
            optimal_exit = max_price
            actual_pnl = (actual_exit - entry) * quantity
            optimal_pnl = (optimal_exit - entry) * quantity
            missed_profit = optimal_pnl - actual_pnl
            could_have_done_better = missed_profit > 0

            result["optimal_exit_analysis"] = {
                "type": "long",
                "best_possible_exit": optimal_exit,
                "worst_possible_exit": min_price,
                "actual_exit": actual_exit,
                "best_possible_pnl": optimal_pnl,
                "worst_possible_pnl": (min_price - entry) * quantity,
                "actual_pnl": actual_pnl,
                "exit_efficiency_pct": (actual_pnl / optimal_pnl * 100) if optimal_pnl > 0 else 0,
            }
        else:
            # For short positions, optimal exit would be at min price
            optimal_exit = min_price
            actual_pnl = (entry - actual_exit) * quantity
            optimal_pnl = (entry - optimal_exit) * quantity
            missed_profit = optimal_pnl - actual_pnl
            could_have_done_better = missed_profit > 0

            result["optimal_exit_analysis"] = {
                "type": "short",
                "best_possible_exit": optimal_exit,
                "worst_possible_exit": max_price,
                "actual_exit": actual_exit,
                "best_possible_pnl": optimal_pnl,
                "worst_possible_pnl": (entry - max_price) * quantity,
                "actual_pnl": actual_pnl,
                "exit_efficiency_pct": (actual_pnl / optimal_pnl * 100) if optimal_pnl > 0 else 0,
            }

        result["optimal_exit_price"] = optimal_exit
        result["missed_profit"] = round(missed_profit, 2)
        result["could_have_done_better"] = could_have_done_better

        return result

    def _analyze_positives(self, trade: Trade, optimal: Dict) -> List[str]:
        """Identify what went well in the trade."""
        positives = []

        # Check if profitable
        if trade.profit_loss and trade.profit_loss > 0:
            positives.append(f"Trade was profitable: ${trade.profit_loss:.2f} ({trade.profit_loss_pct:.1f}%)")

        # Check entry score
        if trade.entry_score and trade.entry_score >= 70:
            positives.append(f"Strong entry signal with score of {trade.entry_score:.0f}/100")

        # Check exit reason
        if trade.exit_reason == "PROFIT_TARGET":
            positives.append("Exit was at planned profit target")
        elif trade.exit_reason == "STOP_LOSS" and (trade.profit_loss or 0) < 0:
            positives.append("Stop loss protected from larger losses")

        # Check exit efficiency
        efficiency = optimal.get("optimal_exit_analysis", {}).get("exit_efficiency_pct", 0)
        if efficiency >= 70:
            positives.append(f"Good exit timing - captured {efficiency:.0f}% of possible profit")

        if not positives:
            positives.append("No significant positive factors identified")

        return positives

    def _analyze_negatives(self, trade: Trade, optimal: Dict) -> List[str]:
        """Identify what went wrong in the trade."""
        negatives = []

        # Check if lost money
        if trade.profit_loss and trade.profit_loss < 0:
            negatives.append(f"Trade resulted in loss: ${abs(trade.profit_loss):.2f} ({abs(trade.profit_loss_pct):.1f}%)")

        # Check missed profit
        missed = optimal.get("missed_profit", 0)
        if missed and missed > 0:
            negatives.append(f"Left ${missed:.2f} on the table with suboptimal exit timing")

        # Check entry score
        if trade.entry_score and trade.entry_score < 60:
            negatives.append(f"Entry signal was weak at {trade.entry_score:.0f}/100")

        # Check exit reason
        if trade.exit_reason == "TIME_STOP":
            negatives.append("Trade held too long without movement")

        # Check exit efficiency
        efficiency = optimal.get("optimal_exit_analysis", {}).get("exit_efficiency_pct", 0)
        if efficiency < 50:
            negatives.append(f"Poor exit timing - only captured {efficiency:.0f}% of possible profit")

        if not negatives:
            negatives.append("No significant negative factors identified")

        return negatives

    def _generate_lessons(self, trade: Trade, optimal: Dict) -> str:
        """Generate key lessons learned from this trade."""
        lessons = []

        # Lesson from exit timing
        efficiency = optimal.get("optimal_exit_analysis", {}).get("exit_efficiency_pct", 0)
        if efficiency < 50:
            lessons.append("Consider using trailing stops to capture more of a price move")
        elif efficiency >= 80:
            lessons.append("Exit timing was excellent - maintain current strategy")

        # Lesson from entry
        if trade.entry_score:
            if trade.entry_score < 60 and (trade.profit_loss or 0) < 0:
                lessons.append("Avoid taking trades with low confidence scores")
            elif trade.entry_score >= 80 and (trade.profit_loss or 0) > 0:
                lessons.append("High-confidence entries continue to perform well")

        # Lesson from exit reason
        if trade.exit_reason == "STOP_LOSS":
            if (trade.profit_loss or 0) < 0:
                lessons.append("Stop loss prevented larger loss - risk management working")
            else:
                lessons.append("Review stop loss placement - may have been too tight")
        elif trade.exit_reason == "TIME_STOP":
            lessons.append("Consider shorter holding periods or more active management")

        # Lesson from duration
        if trade.entry_time and trade.exit_time:
            duration_hours = (trade.exit_time - trade.entry_time).total_seconds() / 3600
            if duration_hours > 168 and (trade.profit_loss or 0) < 0:  # > 1 week
                lessons.append("Long-duration losing trades may indicate thesis was wrong - exit sooner")

        return " | ".join(lessons) if lessons else "No specific lessons identified for this trade."

    async def _generate_ai_summary(self, trade: Trade, analysis: Dict) -> str:
        """Generate an AI-powered human-readable summary of the trade."""
        if not self.openai_client:
            return "AI summary unavailable - OpenAI API key not configured"

        try:
            prompt = f"""Analyze this completed trade and provide a concise 2-3 sentence summary explaining what happened and the key takeaway.

Trade Details:
- Symbol: {trade.symbol}
- Type: {trade.side} ({trade.trade_type or 'unknown'})
- Entry: ${trade.entry_price:.2f} at {trade.entry_time}
- Exit: ${trade.exit_price:.2f} at {trade.exit_time}
- Result: ${trade.profit_loss:.2f} ({trade.profit_loss_pct:.1f}%)
- Exit Reason: {trade.exit_reason}
- Entry Signal Score: {trade.entry_score or 'N/A'}/100

Analysis:
- What went well: {', '.join(analysis.get('what_went_well', []))}
- What went wrong: {', '.join(analysis.get('what_went_wrong', []))}
- Missed profit: ${analysis.get('missed_profit', 0):.2f}
- Exit efficiency: {analysis.get('optimal_exit_analysis', {}).get('exit_efficiency_pct', 0):.0f}%

Write a brief, professional summary (2-3 sentences) that a trader would find helpful."""

            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a trading analyst providing concise post-trade analysis."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.7,
            )

            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"AI summary generation failed: {str(e)}"

    def _format_duration(self, delta: timedelta) -> str:
        """Format a timedelta into human-readable string."""
        total_hours = delta.total_seconds() / 3600
        if total_hours < 1:
            return f"{int(delta.total_seconds() / 60)} minutes"
        elif total_hours < 24:
            return f"{total_hours:.1f} hours"
        else:
            return f"{delta.days} days, {int(total_hours % 24)} hours"

    async def get_trade_analysis(self, trade_id: int) -> Optional[Dict]:
        """Get existing analysis for a trade, or analyze if not yet done."""
        db = SessionLocal()
        try:
            trade = db.query(Trade).filter(Trade.id == trade_id).first()
            if not trade:
                return None

            # Return existing analysis if available
            if trade.post_mortem_analysis:
                return trade.post_mortem_analysis

            # Otherwise, generate new analysis
            return await self.analyze_trade(trade_id)
        finally:
            db.close()

    async def get_daily_summary(self, date: datetime = None) -> Dict[str, Any]:
        """Generate summary of all trades for a given day."""
        if date is None:
            date = datetime.now()

        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        db = SessionLocal()
        try:
            trades = db.query(Trade).filter(
                Trade.exit_time >= start_of_day,
                Trade.exit_time < end_of_day,
                Trade.exit_time != None
            ).all()

            if not trades:
                return {
                    "date": date.date().isoformat(),
                    "message": "No completed trades on this date",
                    "total_trades": 0,
                }

            total_pnl = sum(t.profit_loss or 0 for t in trades)
            winning = [t for t in trades if (t.profit_loss or 0) > 0]
            losing = [t for t in trades if (t.profit_loss or 0) <= 0]

            return {
                "date": date.date().isoformat(),
                "total_trades": len(trades),
                "winning_trades": len(winning),
                "losing_trades": len(losing),
                "win_rate": len(winning) / len(trades) * 100 if trades else 0,
                "total_pnl": round(total_pnl, 2),
                "best_trade": {
                    "symbol": max(trades, key=lambda t: t.profit_loss or 0).symbol,
                    "pnl": max(t.profit_loss or 0 for t in trades),
                },
                "worst_trade": {
                    "symbol": min(trades, key=lambda t: t.profit_loss or 0).symbol,
                    "pnl": min(t.profit_loss or 0 for t in trades),
                },
                "trades": [
                    {
                        "id": t.id,
                        "symbol": t.symbol,
                        "pnl": t.profit_loss,
                        "pnl_pct": t.profit_loss_pct,
                        "exit_reason": t.exit_reason,
                    }
                    for t in trades
                ],
            }
        finally:
            db.close()

    async def get_weekly_report(self) -> Dict[str, Any]:
        """Generate a weekly performance report with insights."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        db = SessionLocal()
        try:
            trades = db.query(Trade).filter(
                Trade.exit_time >= start_date,
                Trade.exit_time <= end_date,
                Trade.exit_time != None
            ).all()

            if not trades:
                return {
                    "period": f"{start_date.date()} to {end_date.date()}",
                    "message": "No completed trades this week",
                    "total_trades": 0,
                }

            total_pnl = sum(t.profit_loss or 0 for t in trades)
            winning = [t for t in trades if (t.profit_loss or 0) > 0]

            # Group by symbol
            by_symbol = {}
            for t in trades:
                if t.symbol not in by_symbol:
                    by_symbol[t.symbol] = {"trades": 0, "pnl": 0}
                by_symbol[t.symbol]["trades"] += 1
                by_symbol[t.symbol]["pnl"] += t.profit_loss or 0

            # Group by exit reason
            by_reason = {}
            for t in trades:
                reason = t.exit_reason or "UNKNOWN"
                if reason not in by_reason:
                    by_reason[reason] = 0
                by_reason[reason] += 1

            report = {
                "period": f"{start_date.date()} to {end_date.date()}",
                "total_trades": len(trades),
                "winning_trades": len(winning),
                "losing_trades": len(trades) - len(winning),
                "win_rate": len(winning) / len(trades) * 100,
                "total_pnl": round(total_pnl, 2),
                "avg_pnl_per_trade": round(total_pnl / len(trades), 2),
                "best_symbol": max(by_symbol.items(), key=lambda x: x[1]["pnl"])[0] if by_symbol else None,
                "worst_symbol": min(by_symbol.items(), key=lambda x: x[1]["pnl"])[0] if by_symbol else None,
                "by_symbol": by_symbol,
                "by_exit_reason": by_reason,
            }

            # Generate AI insights if available
            if self.openai_client:
                report["ai_insights"] = await self._generate_weekly_insights(report)

            return report
        finally:
            db.close()

    async def _generate_weekly_insights(self, report: Dict) -> str:
        """Generate AI insights for weekly report."""
        if not self.openai_client:
            return "AI insights unavailable"

        try:
            prompt = f"""Analyze this weekly trading report and provide 3 actionable insights:

Weekly Performance:
- Total Trades: {report['total_trades']}
- Win Rate: {report['win_rate']:.1f}%
- Total P&L: ${report['total_pnl']:.2f}
- Best Symbol: {report.get('best_symbol', 'N/A')}
- Worst Symbol: {report.get('worst_symbol', 'N/A')}
- Exit Reasons: {report.get('by_exit_reason', {})}

Provide 3 brief, actionable insights to improve performance."""

            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a trading coach providing weekly performance feedback."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.7,
            )

            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"AI insights generation failed: {str(e)}"
