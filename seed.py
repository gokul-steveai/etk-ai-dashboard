import asyncio
import os
import sys
from datetime import datetime, timezone

from sqlalchemy import select

from database import AsyncSessionLocal, engine
from models import SubscriptionPlan
from schemas import PlanName

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


async def seed_subscription_plans():
    print("⏳ Connecting to MySQL instance via aiomysql execution thread...")
    async with AsyncSessionLocal() as db:
        try:
            # Check if plans are already initialized
            result = await db.execute(
                select(SubscriptionPlan).filter(SubscriptionPlan.name == PlanName.FREE)
            )
            existing_free = result.scalars().first()

            if existing_free:
                print(
                    "ℹ️ Subscription tiers are already seeded in MySQL. Skipping execution."
                )
                return

            print("🌱 Injecting specification profiles for FREE and BASIC tiers...")

            free_plan = SubscriptionPlan(
                name=PlanName.FREE,
                description="Limited 'Teaser' access for initial engagement.",
                max_saved_queries=0,
                max_compare_countries=2,
                features={
                    "time_limit_gate": True,
                    "export_formats": False,
                    "risk_intelligence": False,
                    "watchlist_access": False,
                    "partner_access": False,
                },
                created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )

            basic_plan = SubscriptionPlan(
                name=PlanName.BASIC,
                description="Entry-level market access for curious professionals ($39/mo).",
                max_saved_queries=2,
                max_compare_countries=3,
                features={
                    "time_limit_gate": False,
                    "export_formats": False,
                    "risk_intelligence": False,
                    "watchlist_access": False,
                    "partner_access": False,
                },
                created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            )

            db.add_all([free_plan, basic_plan])
            await db.commit()
            print("✅ Production subscription templates applied successfully!")

        except Exception as e:
            await db.rollback()
            print(f"❌ Error encountered during data database mutation seeding: {e}")
        finally:
            await db.close()


async def main():
    try:
        await seed_subscription_plans()
    finally:
        print("🔌 Closing background database connection pools...")
        await engine.dispose()
        print("👋 Clean exit achieved.")


if __name__ == "__main__":
    asyncio.run(main())
