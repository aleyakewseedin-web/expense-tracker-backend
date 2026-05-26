import httpx
from datetime import date
from sqlalchemy.orm import Session
from app.models.currency import CurrencySnapshot
from app.models.currency import CurrencySnapshot
from fastapi import HTTPException

FRANKFURTER_URL = "https://api.frankfurter.dev/v1"

SUPPORTED_CURRENCIES = {
    "AUD", "BGN", "BRL", "CAD", "CHF", "CNY", "CZK", "DKK",
    "EUR", "GBP", "HKD", "HUF", "IDR", "ILS", "INR", "ISK",
    "JPY", "KRW", "MXN", "MYR", "NOK", "NZD", "PHP", "PLN",
    "RON", "SEK", "SGD", "THB", "TRY", "USD", "ZAR"
}
async def get_exchange_rate(
    base_currency: str,
    target_currency: str,
    db: Session,
    expense_date: date = None
) -> float:
    # If same currency, rate is 1

# Validate currency codes first
    if base_currency.upper() not in SUPPORTED_CURRENCIES:
        raise HTTPException(
            status_code=400,
            detail=f"Currency '{base_currency}' is not supported. Supported currencies: {', '.join(sorted(SUPPORTED_CURRENCIES))}"
        )

    if base_currency.upper() == target_currency.upper():
        return 1.0

    check_date = expense_date or date.today()

    # Check if we already have this rate in our database
    existing = db.query(CurrencySnapshot).filter(
        CurrencySnapshot.base_currency == base_currency.upper(),
        CurrencySnapshot.target_currency == target_currency.upper(),
        CurrencySnapshot.snapshot_date == check_date
    ).first()

    if existing:
        return float(existing.exchange_rate)

    # Not in database — fetch from frankfurter.app
    try:
        async with httpx.AsyncClient() as client:
            url = f"{FRANKFURTER_URL}/{check_date}?base={base_currency.upper()}&symbols={target_currency.upper()}"
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            data = response.json()

        rate = data["rates"][target_currency.upper()]
        actual_date = date.fromisoformat(data["date"])  # may differ on weekends

        # Save to database so we don't call the API again today
        snapshot = CurrencySnapshot(
            base_currency=base_currency.upper(),
            target_currency=target_currency.upper(),
            exchange_rate=rate,
            snapshot_date=actual_date
        )
        db.add(snapshot)
        db.commit()

        return float(rate)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Could not fetch exchange rate. Please try again later."
        )