#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def format_wait(ts: int) -> str:
    dt_utc = datetime.fromtimestamp(ts, tz=timezone.utc)
    return dt_utc.strftime("%Y-%m-%d %H:%M:%S %Z")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Request Ostium testnet faucet USDC for delegate wallet"
    )
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Path to env file (default: .env)",
    )
    parser.add_argument(
        "--private-key",
        default=None,
        help="Delegate private key (default: OSTIUM_DELEGATE_PRIVATE_KEY from env)",
    )
    parser.add_argument(
        "--rpc-url",
        default=None,
        help="Arbitrum Sepolia RPC URL (default: OSTIUM_TESTNET_RPC_URL from env)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        from ostium_python_sdk.config import NetworkConfig
        from ostium_python_sdk.sdk import OstiumSDK
    except ModuleNotFoundError:
        print(
            "ERROR: Missing dependency 'ostium-python-sdk'. "
            "Install with: pip install -r requirements.txt"
        )
        return 1

    load_env_file(Path(args.env_file))

    private_key = (
        args.private_key
        or os.getenv("OSTIUM_DELEGATE_PRIVATE_KEY")
        or os.getenv("PRIVATE_KEY")
    )
    rpc_url = args.rpc_url or os.getenv("OSTIUM_TESTNET_RPC_URL") or os.getenv("RPC_URL")

    if not private_key:
        print("ERROR: Missing private key. Set OSTIUM_DELEGATE_PRIVATE_KEY or pass --private-key.")
        return 1
    if not rpc_url:
        print("ERROR: Missing RPC URL. Set OSTIUM_TESTNET_RPC_URL or pass --rpc-url.")
        return 1

    try:
        sdk = OstiumSDK(
            network=NetworkConfig.testnet(),
            private_key=private_key,
            rpc_url=rpc_url,
        )
        address = sdk.ostium.get_public_address()
        print(f"Wallet: {address}")

        if sdk.faucet is None:
            print("ERROR: Faucet is unavailable for this network.")
            return 1

        token_amount_raw = sdk.faucet.get_token_amount()
        token_amount_human = Decimal(token_amount_raw) / Decimal(10**6)
        print(f"Faucet amount per request: {token_amount_human} USDC")

        if not sdk.faucet.can_request_tokens(address):
            next_ts = sdk.faucet.get_next_request_time(address)
            print(f"Not eligible yet. Next request time: {format_wait(next_ts)}")
            return 2

        receipt = sdk.faucet.request_tokens()
        tx_hash = receipt["transactionHash"].hex() if receipt.get("transactionHash") else None
        print("Faucet request submitted successfully.")
        if tx_hash:
            print(f"Tx hash: {tx_hash}")
            print(f"Explorer: https://sepolia.arbiscan.io/tx/{tx_hash}")
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
