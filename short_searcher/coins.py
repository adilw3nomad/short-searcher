import re

COIN_MAP: dict[str, str] = {
    "BTC": "Bitcoin",
    "ETH": "Ethereum",
    "XRP": "Ripple",
    "SOL": "Solana",
    "ADA": "Cardano",
    "DOGE": "Dogecoin",
    "SHIB": "Shiba Inu",
    "LUNC": "Terra Luna Classic",
    "BNB": "BNB",
    "AVAX": "Avalanche",
    "LINK": "Chainlink",
    "DOT": "Polkadot",
    "MATIC": "Polygon",
    "LTC": "Litecoin",
    "PEPE": "Pepe",
}

# name -> ticker, for matching spelled-out coin names
_NAME_TO_TICKER = {name.lower(): ticker for ticker, name in COIN_MAP.items()}


def extract_coins(title: str, description: str) -> list[str]:
    text = f"{title} {description}"
    found: set[str] = set()
    for ticker in COIN_MAP:
        if re.search(rf"\b{re.escape(ticker)}\b", text):  # case-sensitive: tickers are uppercase
            found.add(ticker)
    for name, ticker in _NAME_TO_TICKER.items():
        if re.search(rf"\b{re.escape(name)}\b", text, re.IGNORECASE):
            found.add(ticker)
    return sorted(found)
