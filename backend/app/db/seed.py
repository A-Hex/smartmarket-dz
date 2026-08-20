# backend/app/db/seed.py
"""
Seed script: creates a demo company, a demo owner user, and a realistic
Algerian retail sample CSV so the full pipeline can be exercised end-to-end.

Run with:  docker-compose exec backend python -m app.db.seed
"""
import asyncio
import os
import random
from datetime import datetime, timedelta, timezone

import pandas as pd
from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.company import Company
from app.models.user import User, UserRole

DEMO_COMPANY_NAME = "Demo Algérie Retail"
DEMO_COMPANY_SLUG = "demo-algerie-retail"
DEMO_USER_EMAIL = "demo@smartmarket.dz"
DEMO_USER_PASSWORD = "Demo12345!"
DEMO_CSV_FILENAME = "demo_sales_algeria.csv"

REGIONS = ["Alger", "Oran", "Constantine", "Annaba", "Batna", "Sétif"]
PRODUCTS = ["Smartphone", "Laptop", "Casque audio", "Montre connectée", "Tablette", "Enceinte"]


def _generate_demo_dataframe(n_rows: int = 500) -> pd.DataFrame:
    """Build a synthetic-but-realistic Algerian retail dataset for the demo pipeline."""
    random.seed(42)
    start_date = datetime(2024, 1, 1)
    rows = []
    for i in range(n_rows):
        date = start_date + timedelta(days=random.randint(0, 540))
        product = random.choice(PRODUCTS)
        region = random.choice(REGIONS)
        price = round(random.uniform(2000, 180000), 2)
        marketing_spend = round(random.uniform(0, 5000), 2)
        quantity = random.randint(1, 10)
        # deliberately correlate sales with marketing_spend and (inversely) price
        # and inject a collinear feature (marketing_spend_2) for the VIF-FAIL demo case
        marketing_spend_2 = marketing_spend * 0.98 + random.uniform(-5, 5)
        noise = random.gauss(0, 500)
        sales = max(
            0,
            price * quantity * 0.15 + marketing_spend * 8 - price * 0.02 + noise,
        )
        rows.append(
            {
                "date": date.strftime("%Y-%m-%d"),
                "product": product,
                "region": region,
                "customer_id": f"CUST-{random.randint(1000, 1500)}",
                "price": price,
                "quantity": quantity,
                "marketing_spend": marketing_spend,
                "marketing_spend_2": round(marketing_spend_2, 2),
                "sales": round(sales, 2),
            }
        )
    # sprinkle a few missing values and an outlier row, for the cleaning demo
    df = pd.DataFrame(rows)
    for col in ["price", "marketing_spend"]:
        df.loc[df.sample(frac=0.03, random_state=1).index, col] = None
    df.loc[0, "sales"] = df["sales"].max() * 8  # outlier
    return df


async def seed() -> None:
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Company).where(Company.slug == DEMO_COMPANY_SLUG))
        company = result.scalar_one_or_none()
        if company is None:
            company = Company(name=DEMO_COMPANY_NAME, slug=DEMO_COMPANY_SLUG, country="DZ")
            db.add(company)
            await db.flush()
            print(f"Created demo company: {company.name} ({company.id})")
        else:
            print(f"Demo company already exists: {company.name} ({company.id})")

        result = await db.execute(select(User).where(User.email == DEMO_USER_EMAIL))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                company_id=company.id,
                email=DEMO_USER_EMAIL,
                hashed_password=hash_password(DEMO_USER_PASSWORD),
                full_name="Demo Owner",
                role=UserRole.OWNER,
                is_active=True,
            )
            db.add(user)
            print(f"Created demo user: {DEMO_USER_EMAIL} / {DEMO_USER_PASSWORD}")
        else:
            print(f"Demo user already exists: {DEMO_USER_EMAIL}")

        await db.commit()

    csv_path = os.path.join(settings.UPLOAD_DIR, DEMO_CSV_FILENAME)
    if not os.path.exists(csv_path):
        df = _generate_demo_dataframe()
        df.to_csv(csv_path, index=False)
        print(f"Wrote demo dataset CSV to {csv_path} ({len(df)} rows)")
    else:
        print(f"Demo dataset CSV already exists at {csv_path}")

    print("\nSeed complete. Log in with:")
    print(f"  email:    {DEMO_USER_EMAIL}")
    print(f"  password: {DEMO_USER_PASSWORD}")
    print(f"  demo CSV: {csv_path}  (upload it via POST /api/v1/datasets once Phase 2 ships)")


if __name__ == "__main__":
    asyncio.run(seed())
