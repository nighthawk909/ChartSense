"""
Settings API Routes
Endpoints for bot configuration and settings management
"""
from fastapi import APIRouter, HTTPException
from typing import Optional
from datetime import datetime

from models.bot import (
    BotSettings,
    BotSettingsResponse,
    UpdateSettingsRequest,
)
from database.connection import SessionLocal
from database.models import BotConfiguration
from services.trading_bot import get_trading_bot

router = APIRouter()


def _get_default_settings() -> BotSettings:
    """Return default settings"""
    return BotSettings(
        enabled_symbols=["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"],
        max_positions=5,
        max_position_size_pct=0.20,
        risk_per_trade_pct=0.02,
        max_daily_loss_pct=0.03,
        default_stop_loss_pct=0.05,
        entry_score_threshold=70.0,
        swing_profit_target_pct=0.08,
        longterm_profit_target_pct=0.15,
        paper_trading=False,
        trading_hours_only=True,
        auto_optimize=True,
    )


@router.get("/", response_model=BotSettingsResponse)
async def get_settings():
    """
    Get current bot settings.
    """
    db = SessionLocal()
    try:
        config = db.query(BotConfiguration).filter(
            BotConfiguration.is_active == True
        ).first()

        if not config:
            # Return defaults if no config exists
            return BotSettingsResponse(
                settings=_get_default_settings(),
                config_name="default",
                last_updated=None,
            )

        settings = BotSettings(
            enabled_symbols=config.enabled_symbols or [],
            max_positions=config.max_positions,
            max_position_size_pct=config.max_position_size_pct,
            risk_per_trade_pct=config.risk_per_trade_pct,
            max_daily_loss_pct=config.max_daily_loss_pct,
            default_stop_loss_pct=config.default_stop_loss_pct,
            entry_score_threshold=config.entry_score_threshold,
            swing_profit_target_pct=config.swing_profit_target_pct,
            longterm_profit_target_pct=config.longterm_profit_target_pct,
            paper_trading=config.paper_trading,
            trading_hours_only=config.trading_hours_only,
            auto_optimize=config.auto_optimize,
        )

        return BotSettingsResponse(
            settings=settings,
            config_name=config.name,
            last_updated=config.updated_at,
        )
    finally:
        db.close()


@router.put("/", response_model=BotSettingsResponse)
async def update_settings(request: UpdateSettingsRequest):
    """
    Update bot settings.

    Changes are applied immediately if the bot is running.
    """
    db = SessionLocal()
    try:
        config = db.query(BotConfiguration).filter(
            BotConfiguration.is_active == True
        ).first()

        settings = request.settings

        if not config:
            # Create new config
            config = BotConfiguration(
                name="default",
                enabled_symbols=settings.enabled_symbols,
                max_positions=settings.max_positions,
                max_position_size_pct=settings.max_position_size_pct,
                risk_per_trade_pct=settings.risk_per_trade_pct,
                max_daily_loss_pct=settings.max_daily_loss_pct,
                default_stop_loss_pct=settings.default_stop_loss_pct,
                entry_score_threshold=settings.entry_score_threshold,
                swing_profit_target_pct=settings.swing_profit_target_pct,
                longterm_profit_target_pct=settings.longterm_profit_target_pct,
                paper_trading=settings.paper_trading,
                trading_hours_only=settings.trading_hours_only,
                auto_optimize=settings.auto_optimize,
                is_active=True,
            )
            db.add(config)
        else:
            # Update existing config
            config.enabled_symbols = settings.enabled_symbols
            config.max_positions = settings.max_positions
            config.max_position_size_pct = settings.max_position_size_pct
            config.risk_per_trade_pct = settings.risk_per_trade_pct
            config.max_daily_loss_pct = settings.max_daily_loss_pct
            config.default_stop_loss_pct = settings.default_stop_loss_pct
            config.entry_score_threshold = settings.entry_score_threshold
            config.swing_profit_target_pct = settings.swing_profit_target_pct
            config.longterm_profit_target_pct = settings.longterm_profit_target_pct
            config.paper_trading = settings.paper_trading
            config.trading_hours_only = settings.trading_hours_only
            config.auto_optimize = settings.auto_optimize
            config.updated_at = datetime.now()

        db.commit()
        db.refresh(config)

        # Apply to running bot
        bot = get_trading_bot()
        bot._apply_config({
            "enabled_symbols": settings.enabled_symbols,
            "paper_trading": settings.paper_trading,
            "trading_hours_only": settings.trading_hours_only,
            "entry_score_threshold": settings.entry_score_threshold,
            "swing_profit_target_pct": settings.swing_profit_target_pct,
            "longterm_profit_target_pct": settings.longterm_profit_target_pct,
            "max_positions": settings.max_positions,
            "risk_per_trade_pct": settings.risk_per_trade_pct,
            "max_daily_loss_pct": settings.max_daily_loss_pct,
        })

        return BotSettingsResponse(
            settings=settings,
            config_name=config.name,
            last_updated=config.updated_at,
        )
    finally:
        db.close()


@router.post("/reset")
async def reset_settings():
    """
    Reset settings to defaults.
    """
    db = SessionLocal()
    try:
        # Delete all configs
        db.query(BotConfiguration).delete()

        # Create default config
        defaults = _get_default_settings()
        config = BotConfiguration(
            name="default",
            enabled_symbols=defaults.enabled_symbols,
            max_positions=defaults.max_positions,
            max_position_size_pct=defaults.max_position_size_pct,
            risk_per_trade_pct=defaults.risk_per_trade_pct,
            max_daily_loss_pct=defaults.max_daily_loss_pct,
            default_stop_loss_pct=defaults.default_stop_loss_pct,
            entry_score_threshold=defaults.entry_score_threshold,
            swing_profit_target_pct=defaults.swing_profit_target_pct,
            longterm_profit_target_pct=defaults.longterm_profit_target_pct,
            paper_trading=defaults.paper_trading,
            trading_hours_only=defaults.trading_hours_only,
            auto_optimize=defaults.auto_optimize,
            is_active=True,
        )
        db.add(config)
        db.commit()

        return {
            "success": True,
            "message": "Settings reset to defaults",
        }
    finally:
        db.close()


@router.get("/presets")
async def get_presets():
    """
    Get available configuration presets.
    """
    return {
        "presets": [
            {
                "name": "conservative",
                "description": "Lower risk, fewer trades, tighter stops",
                "settings": {
                    "max_positions": 3,
                    "max_position_size_pct": 0.15,
                    "risk_per_trade_pct": 0.01,
                    "max_daily_loss_pct": 0.02,
                    "entry_score_threshold": 80.0,
                    "swing_profit_target_pct": 0.05,
                    "longterm_profit_target_pct": 0.10,
                },
            },
            {
                "name": "moderate",
                "description": "Balanced risk and reward (default)",
                "settings": {
                    "max_positions": 5,
                    "max_position_size_pct": 0.20,
                    "risk_per_trade_pct": 0.02,
                    "max_daily_loss_pct": 0.03,
                    "entry_score_threshold": 70.0,
                    "swing_profit_target_pct": 0.08,
                    "longterm_profit_target_pct": 0.15,
                },
            },
            {
                "name": "aggressive",
                "description": "Higher risk, more trades, larger positions",
                "settings": {
                    "max_positions": 8,
                    "max_position_size_pct": 0.25,
                    "risk_per_trade_pct": 0.03,
                    "max_daily_loss_pct": 0.05,
                    "entry_score_threshold": 65.0,
                    "swing_profit_target_pct": 0.12,
                    "longterm_profit_target_pct": 0.20,
                },
            },
        ]
    }


@router.post("/presets/{preset_name}")
async def apply_preset(preset_name: str):
    """
    Apply a configuration preset.
    """
    presets = {
        "conservative": {
            "max_positions": 3,
            "max_position_size_pct": 0.15,
            "risk_per_trade_pct": 0.01,
            "max_daily_loss_pct": 0.02,
            "entry_score_threshold": 80.0,
            "swing_profit_target_pct": 0.05,
            "longterm_profit_target_pct": 0.10,
        },
        "moderate": {
            "max_positions": 5,
            "max_position_size_pct": 0.20,
            "risk_per_trade_pct": 0.02,
            "max_daily_loss_pct": 0.03,
            "entry_score_threshold": 70.0,
            "swing_profit_target_pct": 0.08,
            "longterm_profit_target_pct": 0.15,
        },
        "aggressive": {
            "max_positions": 8,
            "max_position_size_pct": 0.25,
            "risk_per_trade_pct": 0.03,
            "max_daily_loss_pct": 0.05,
            "entry_score_threshold": 65.0,
            "swing_profit_target_pct": 0.12,
            "longterm_profit_target_pct": 0.20,
        },
    }

    if preset_name not in presets:
        raise HTTPException(status_code=404, detail=f"Preset '{preset_name}' not found")

    preset = presets[preset_name]

    db = SessionLocal()
    try:
        config = db.query(BotConfiguration).filter(
            BotConfiguration.is_active == True
        ).first()

        if not config:
            config = BotConfiguration(name="default", is_active=True)
            db.add(config)

        # Apply preset values
        for key, value in preset.items():
            setattr(config, key, value)

        config.updated_at = datetime.now()
        db.commit()

        return {
            "success": True,
            "message": f"Applied '{preset_name}' preset",
            "settings": preset,
        }
    finally:
        db.close()
