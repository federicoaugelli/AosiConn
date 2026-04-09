from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
    Depends,
    HTTPException,
    Query,
)
from typing import Optional
import logging
import json

from utils.websocket_manager import manager
from utils.metrics_service import metrics_calculator
from auth.auth_bearer import JWTBearer
from auth.auth_handler import decodeJWT
from db.database import get_db
from sqlalchemy.orm import Session
from db import crud

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_user_id_from_token(token: str) -> Optional[int]:
    """Decode JWT token and extract user_id"""
    try:
        payload = decodeJWT(token)
        if payload and "user_id" in payload:
            return payload["user_id"]
    except Exception as e:
        logger.error(f"Error decoding token: {e}")
    return None


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket, token: str = Query(...), db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for real-time updates.

    Query Parameters:
    - token: JWT authentication token

    Messages from client:
    - subscribe: {"action": "subscribe", "channels": ["trades", "positions", "balance", "metrics"]}
    - unsubscribe: {"action": "unsubscribe", "channels": ["trades"]}
    - ping: {"action": "ping"}
    - get_performance: {"action": "get_performance", "exchange": "hyperliquid", "days": 30}
    - get_positions: {"action": "get_positions", "exchange": "hyperliquid"}
    - get_balance: {"action": "get_balance", "exchange": "hyperliquid"}
    """
    # Authenticate
    user_id = await get_user_id_from_token(token)
    if not user_id:
        await websocket.close(code=4001, reason="Invalid token")
        return

    await manager.connect(websocket, user_id)

    try:
        # Send initial welcome message
        await websocket.send_json(
            {
                "type": "connection_established",
                "data": {
                    "user_id": user_id,
                    "message": "Connected to AosiConn WebSocket",
                },
                "timestamp": "",
            }
        )

        while True:
            # Receive message from client
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
                action = message.get("action")

                if action == "ping":
                    await websocket.send_json(
                        {"type": "pong", "data": {}, "timestamp": ""}
                    )

                elif action == "subscribe":
                    channels = message.get("channels", [])
                    if user_id in manager.user_metadata:
                        manager.user_metadata[user_id]["subscriptions"] = channels
                    await websocket.send_json(
                        {
                            "type": "subscribed",
                            "data": {"channels": channels},
                            "timestamp": "",
                        }
                    )

                elif action == "get_performance":
                    exchange = message.get("exchange", "hyperliquid")
                    days = message.get("days", 30)

                    performance = metrics_calculator.calculate_performance_summary(
                        db, user_id, exchange, days
                    )

                    await manager.send_performance_update(
                        user_id, performance.model_dump()
                    )

                elif action == "get_positions":
                    exchange = message.get("exchange", "hyperliquid")

                    # Get recent position snapshots
                    snapshots = crud.get_position_snapshots(
                        db, user_id, exchange, hours=1
                    )

                    await websocket.send_json(
                        {
                            "type": "positions_snapshot",
                            "data": [
                                {
                                    "pair": s.pair,
                                    "position_size": s.position_size,
                                    "entry_price": s.entry_price,
                                    "mark_price": s.mark_price,
                                    "unrealized_pnl": s.unrealized_pnl,
                                    "margin_used": s.margin_used,
                                    "leverage": s.leverage,
                                    "timestamp": s.timestamp.isoformat()
                                    if s.timestamp
                                    else None,
                                }
                                for s in snapshots[-10:]  # Last 10 snapshots
                            ],
                            "timestamp": "",
                        }
                    )

                elif action == "get_balance":
                    exchange = message.get("exchange", "hyperliquid")

                    latest = crud.get_latest_balance(db, user_id, exchange)
                    if latest:
                        await manager.send_balance_update(
                            user_id,
                            {
                                "exchange": latest.exchange,
                                "amount": latest.amount,
                                "available": latest.available,
                                "used_margin": latest.used_margin,
                                "unrealized_pnl": latest.unrealized_pnl,
                                "timestamp": latest.timestamp,
                            },
                        )
                    else:
                        await websocket.send_json(
                            {"type": "balance_update", "data": None, "timestamp": ""}
                        )

                elif action == "get_equity_curve":
                    exchange = message.get("exchange", "hyperliquid")
                    days = message.get("days", 30)

                    equity_curve = metrics_calculator.generate_equity_curve(
                        db, user_id, exchange, days
                    )

                    await websocket.send_json(
                        {
                            "type": "equity_curve",
                            "data": [
                                {
                                    "timestamp": e.timestamp.isoformat()
                                    if e.timestamp
                                    else None,
                                    "balance": e.balance,
                                    "daily_pnl": e.daily_pnl,
                                    "drawdown": e.drawdown,
                                    "drawdown_pct": e.drawdown_pct,
                                }
                                for e in equity_curve
                            ],
                            "timestamp": "",
                        }
                    )

                elif action == "get_heatmap":
                    exchange = message.get("exchange", "hyperliquid")
                    hours = message.get("hours", 24)

                    heatmap = metrics_calculator.calculate_position_heatmap(
                        db, user_id, exchange, hours
                    )

                    await websocket.send_json(
                        {"type": "position_heatmap", "data": heatmap, "timestamp": ""}
                    )

                elif action == "get_returns":
                    exchange = message.get("exchange", "hyperliquid")

                    returns = metrics_calculator.calculate_returns_by_period(
                        db, user_id, exchange
                    )

                    await websocket.send_json(
                        {"type": "returns", "data": returns, "timestamp": ""}
                    )

                else:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "data": {"message": f"Unknown action: {action}"},
                            "timestamp": "",
                        }
                    )

            except json.JSONDecodeError:
                await websocket.send_json(
                    {
                        "type": "error",
                        "data": {"message": "Invalid JSON"},
                        "timestamp": "",
                    }
                )
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}")
                await websocket.send_json(
                    {"type": "error", "data": {"message": str(e)}, "timestamp": ""}
                )

    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, user_id)
