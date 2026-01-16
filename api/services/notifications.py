"""
Notification Service for Trade Alerts
Sends email/SMS notifications for trade executions and important events
"""
import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class NotificationType(str, Enum):
    """Types of notifications"""
    TRADE_EXECUTED = "trade_executed"
    POSITION_OPENED = "position_opened"
    POSITION_CLOSED = "position_closed"
    STOP_LOSS_HIT = "stop_loss_hit"
    TAKE_PROFIT_HIT = "take_profit_hit"
    DAILY_SUMMARY = "daily_summary"
    ALERT = "alert"
    ERROR = "error"


@dataclass
class Notification:
    """Notification data structure"""
    type: NotificationType
    title: str
    message: str
    symbol: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class NotificationService:
    """
    Service for sending notifications via email.
    Can be extended for SMS (Twilio), push notifications, etc.
    """

    def __init__(self):
        # Email settings from environment
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.from_email = os.getenv("NOTIFICATION_FROM_EMAIL", "")
        self.to_emails = os.getenv("NOTIFICATION_TO_EMAILS", "").split(",")

        # Check if email is configured
        self.email_enabled = bool(self.smtp_user and self.smtp_password and self.to_emails[0])

        # Notification history
        self._history: List[Notification] = []
        self._max_history = 100

        if self.email_enabled:
            logger.info("Email notifications enabled")
        else:
            logger.info("Email notifications disabled (SMTP not configured)")

    def send(self, notification: Notification) -> bool:
        """
        Send a notification.

        Args:
            notification: Notification to send

        Returns:
            True if sent successfully
        """
        # Store in history
        self._history.append(notification)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        # Log the notification
        logger.info(f"Notification: [{notification.type.value}] {notification.title}")

        # Send email if configured
        if self.email_enabled:
            return self._send_email(notification)

        return True

    def _send_email(self, notification: Notification) -> bool:
        """Send email notification"""
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"ChartSense: {notification.title}"
            msg["From"] = self.from_email
            msg["To"] = ", ".join(filter(None, self.to_emails))

            # Plain text version
            text = f"""
ChartSense Trading Bot Alert
=============================

{notification.title}

{notification.message}

Symbol: {notification.symbol or 'N/A'}
Time: {notification.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
Type: {notification.type.value}

---
This is an automated message from ChartSense Trading Bot.
            """

            # HTML version
            html = f"""
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
    <div style="background: linear-gradient(135deg, #1e3a5f 0%, #0f172a 100%); padding: 20px; border-radius: 10px;">
        <h2 style="color: #3b82f6; margin: 0;">ChartSense Trading Bot</h2>
    </div>

    <div style="padding: 20px; background: #f8fafc; border-radius: 10px; margin-top: 10px;">
        <h3 style="color: #1e293b; margin-top: 0;">{notification.title}</h3>

        <p style="color: #475569; line-height: 1.6;">
            {notification.message}
        </p>

        <div style="background: #e2e8f0; padding: 15px; border-radius: 5px; margin-top: 15px;">
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 5px 0; color: #64748b;">Symbol:</td>
                    <td style="padding: 5px 0; color: #1e293b; font-weight: bold;">{notification.symbol or 'N/A'}</td>
                </tr>
                <tr>
                    <td style="padding: 5px 0; color: #64748b;">Time:</td>
                    <td style="padding: 5px 0; color: #1e293b;">{notification.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</td>
                </tr>
                <tr>
                    <td style="padding: 5px 0; color: #64748b;">Type:</td>
                    <td style="padding: 5px 0; color: #1e293b;">{notification.type.value}</td>
                </tr>
            </table>
        </div>

        {self._format_data_html(notification.data) if notification.data else ''}
    </div>

    <div style="padding: 15px; text-align: center; color: #94a3b8; font-size: 12px;">
        Automated message from ChartSense Trading Bot
    </div>
</body>
</html>
            """

            msg.attach(MIMEText(text, "plain"))
            msg.attach(MIMEText(html, "html"))

            # Send
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            logger.info(f"Email notification sent: {notification.title}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False

    def _format_data_html(self, data: Dict[str, Any]) -> str:
        """Format additional data as HTML table"""
        if not data:
            return ""

        rows = ""
        for key, value in data.items():
            # Format key
            label = key.replace("_", " ").title()
            # Format value
            if isinstance(value, float):
                formatted_value = f"${value:,.2f}" if "price" in key.lower() or "pnl" in key.lower() else f"{value:.2f}"
            else:
                formatted_value = str(value)

            rows += f"""
            <tr>
                <td style="padding: 5px 0; color: #64748b;">{label}:</td>
                <td style="padding: 5px 0; color: #1e293b;">{formatted_value}</td>
            </tr>
            """

        return f"""
        <div style="background: #dbeafe; padding: 15px; border-radius: 5px; margin-top: 15px;">
            <h4 style="margin: 0 0 10px 0; color: #1e40af;">Details</h4>
            <table style="width: 100%; border-collapse: collapse;">
                {rows}
            </table>
        </div>
        """

    # Convenience methods for common notifications

    def notify_trade_executed(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        order_id: str = None
    ):
        """Send notification for trade execution"""
        self.send(Notification(
            type=NotificationType.TRADE_EXECUTED,
            title=f"{side.upper()} {symbol} Executed",
            message=f"Successfully executed {side.upper()} order for {quantity} shares of {symbol} at ${price:.2f}",
            symbol=symbol,
            data={
                "side": side,
                "quantity": quantity,
                "price": price,
                "total_value": quantity * price,
                "order_id": order_id or "N/A"
            }
        ))

    def notify_position_closed(
        self,
        symbol: str,
        quantity: float,
        entry_price: float,
        exit_price: float,
        pnl: float,
        pnl_pct: float,
        exit_reason: str
    ):
        """Send notification for position closure"""
        emoji = "+" if pnl >= 0 else ""
        self.send(Notification(
            type=NotificationType.POSITION_CLOSED,
            title=f"Position Closed: {symbol} ({emoji}${pnl:.2f})",
            message=f"Closed {quantity} shares of {symbol}. Entry: ${entry_price:.2f}, Exit: ${exit_price:.2f}. Reason: {exit_reason}",
            symbol=symbol,
            data={
                "quantity": quantity,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "pnl": pnl,
                "pnl_pct": pnl_pct,
                "exit_reason": exit_reason
            }
        ))

    def notify_stop_loss_hit(
        self,
        symbol: str,
        entry_price: float,
        stop_price: float,
        loss: float
    ):
        """Send notification for stop loss trigger"""
        self.send(Notification(
            type=NotificationType.STOP_LOSS_HIT,
            title=f"STOP LOSS: {symbol} (-${abs(loss):.2f})",
            message=f"Stop loss triggered for {symbol}. Entry was ${entry_price:.2f}, stopped out at ${stop_price:.2f}",
            symbol=symbol,
            data={
                "entry_price": entry_price,
                "stop_price": stop_price,
                "loss": loss
            }
        ))

    def notify_take_profit_hit(
        self,
        symbol: str,
        entry_price: float,
        exit_price: float,
        profit: float
    ):
        """Send notification for take profit trigger"""
        self.send(Notification(
            type=NotificationType.TAKE_PROFIT_HIT,
            title=f"PROFIT TARGET: {symbol} (+${profit:.2f})",
            message=f"Take profit triggered for {symbol}. Entry was ${entry_price:.2f}, exited at ${exit_price:.2f}",
            symbol=symbol,
            data={
                "entry_price": entry_price,
                "exit_price": exit_price,
                "profit": profit
            }
        ))

    def notify_daily_summary(
        self,
        date: str,
        total_trades: int,
        winning_trades: int,
        total_pnl: float,
        portfolio_value: float
    ):
        """Send daily trading summary"""
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        emoji = "+" if total_pnl >= 0 else ""

        self.send(Notification(
            type=NotificationType.DAILY_SUMMARY,
            title=f"Daily Summary: {emoji}${total_pnl:.2f}",
            message=f"Trading day {date} complete. {total_trades} trades with {win_rate:.1f}% win rate.",
            data={
                "date": date,
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "losing_trades": total_trades - winning_trades,
                "win_rate": f"{win_rate:.1f}%",
                "total_pnl": total_pnl,
                "portfolio_value": portfolio_value
            }
        ))

    def notify_error(self, title: str, message: str, error: str = None):
        """Send error notification"""
        self.send(Notification(
            type=NotificationType.ERROR,
            title=f"ERROR: {title}",
            message=message,
            data={"error_details": error} if error else None
        ))

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get notification history"""
        return [
            {
                "type": n.type.value,
                "title": n.title,
                "message": n.message,
                "symbol": n.symbol,
                "data": n.data,
                "timestamp": n.timestamp.isoformat()
            }
            for n in self._history[-limit:]
        ]


# Singleton instance
_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """Get singleton notification service"""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service
