#!/usr/bin/env python3
"""
GoldShield Trade Logging API
─────────────────────────────
Lightweight HTTP server that receives trade events from the MT5 EA
(via MQL5 WebRequest) and logs them to PostgreSQL.

Endpoints:
    POST /trade/open   — log a new trade entry
    POST /trade/close  — log trade exit + P&L
    GET  /health       — health check

Run:
    python scripts/trade_api.py                  # default port 5555
    python scripts/trade_api.py --port 8080      # custom port
"""

import argparse
import json
import os
import sys
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from db.connection import db_cursor


class TradeHandler(BaseHTTPRequestHandler):

    def _send_json(self, code: int, data: dict):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length))

    def do_GET(self):
        if self.path == "/health":
            self._send_json(200, {"status": "ok", "service": "goldshield-trade-api"})
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self):
        body = self._read_body()

        if self.path == "/trade/open":
            self._handle_open(body)
        elif self.path == "/trade/close":
            self._handle_close(body)
        else:
            self._send_json(404, {"error": "not found"})

    def _handle_open(self, body: dict):
        required = ["direction", "lot_size", "entry_price"]
        missing = [k for k in required if k not in body]
        if missing:
            self._send_json(400, {"error": f"Missing fields: {missing}"})
            return

        with db_cursor() as cur:
            cur.execute("""
                INSERT INTO trades
                    (symbol, direction, lot_size, entry_price,
                     stop_loss, take_profit, param_set_id, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, time
            """, (
                body.get("symbol", "XAUUSD"),
                body["direction"].upper(),
                float(body["lot_size"]),
                float(body["entry_price"]),
                body.get("stop_loss"),
                body.get("take_profit"),
                body.get("param_set_id"),
                body.get("notes", ""),
            ))
            row = cur.fetchone()

        self._send_json(201, {
            "trade_id": row[0],
            "time": row[1].isoformat(),
            "status": "opened",
        })
        print(f"  [OPEN] {body['direction']} {body['lot_size']} @ {body['entry_price']}")

    def _handle_close(self, body: dict):
        required = ["trade_id", "exit_price"]
        missing = [k for k in required if k not in body]
        if missing:
            self._send_json(400, {"error": f"Missing fields: {missing}"})
            return

        with db_cursor() as cur:
            # Get entry info
            cur.execute("SELECT entry_price, direction, lot_size FROM trades WHERE id = %s",
                        (body["trade_id"],))
            trade = cur.fetchone()
            if not trade:
                self._send_json(404, {"error": f"Trade {body['trade_id']} not found"})
                return

            entry_price, direction, lot_size = trade
            exit_price = float(body["exit_price"])

            # Calculate P&L in price units
            if direction == "BUY":
                pnl_pips = exit_price - entry_price
            else:
                pnl_pips = entry_price - exit_price

            pnl = pnl_pips * lot_size

            cur.execute("""
                UPDATE trades SET
                    exit_price = %s,
                    exit_time = NOW(),
                    pnl = %s,
                    pnl_pips = %s,
                    duration_mins = EXTRACT(EPOCH FROM (NOW() - time)) / 60,
                    exit_reason = %s,
                    commission = %s,
                    swap = %s
                WHERE id = %s
            """, (
                exit_price, pnl, pnl_pips,
                body.get("exit_reason", ""),
                body.get("commission", 0),
                body.get("swap", 0),
                body["trade_id"],
            ))

        self._send_json(200, {
            "trade_id": body["trade_id"],
            "pnl": round(pnl, 2),
            "pnl_pips": round(pnl_pips, 2),
            "status": "closed",
        })
        print(f"  [CLOSE] Trade #{body['trade_id']} PnL: {pnl:.2f}")

    def log_message(self, format, *args):
        # Quieter logging
        pass


def main():
    parser = argparse.ArgumentParser(description="GoldShield Trade API")
    parser.add_argument("--port", "-p", type=int, default=5555)
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args()

    server = HTTPServer((args.host, args.port), TradeHandler)
    print(f"GoldShield Trade API running on http://{args.host}:{args.port}")
    print(f"  POST /trade/open   — log entry")
    print(f"  POST /trade/close  — log exit")
    print(f"  GET  /health       — health check")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()


if __name__ == "__main__":
    main()
