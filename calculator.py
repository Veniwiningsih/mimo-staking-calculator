#!/usr/bin/env python3
"""MiMo Staking Calculator - Multi-protocol staking rewards calculator."""

import json
import logging
from typing import Dict, List
from dataclasses import dataclass, asdict

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("staking-calculator")


@dataclass
class StakingPool:
    name: str
    protocol: str
    token: str
    apy: float
    min_stake: float
    lock_period: int
    unbonding_period: int
    commission: float = 0.0
    auto_compound: bool = True

    @property
    def effective_apy(self) -> float:
        return self.apy * (1 - self.commission)

    @property
    def daily_rate(self) -> float:
        return self.effective_apy / 365


class StakingCalculator:
    def __init__(self):
        self.pools: List[StakingPool] = []

    def add_pool(self, pool: StakingPool):
        self.pools.append(pool)

    def calculate_rewards(self, pool: StakingPool, principal: float, days: int, compound: bool = True) -> Dict:
        if principal < pool.min_stake:
            return {"error": f"Minimum stake: {pool.min_stake} {pool.token}", "pool": pool.name}

        rate = pool.effective_apy
        if compound and pool.auto_compound:
            final = principal * (1 + rate / 365) ** days
        else:
            final = principal * (1 + rate * days / 365)

        rewards = final - principal
        daily_earnings = principal * pool.daily_rate
        monthly_earnings = daily_earnings * 30

        return {
            "pool": pool.name,
            "protocol": pool.protocol,
            "token": pool.token,
            "principal": f"{principal:,.2f}",
            "duration_days": days,
            "apy": f"{pool.apy:.2%}",
            "effective_apy": f"{rate:.2%}",
            "commission": f"{pool.commission:.0%}",
            "compound": "Yes" if compound and pool.auto_compound else "No",
            "final_balance": f"{final:,.2f} {pool.token}",
            "total_rewards": f"{rewards:,.2f} {pool.token}",
            "roi": f"{rewards / principal:.2%}",
            "daily_earnings": f"{daily_earnings:,.4f} {pool.token}",
            "monthly_earnings": f"{monthly_earnings:,.2f} {pool.token}",
            "lock_period": f"{pool.lock_period} days",
            "unbonding_period": f"{pool.unbonding_period} days",
        }

    def compare_pools(self, principal: float, days: int) -> List[Dict]:
        results = []
        for pool in self.pools:
            if principal >= pool.min_stake:
                result = self.calculate_rewards(pool, principal, days)
                results.append(result)
        results.sort(key=lambda x: float(x.get("roi", "0%").strip("%")), reverse=True)
        return results

    def break_even_analysis(self, pool: StakingPool, gas_cost: float) -> Dict:
        daily_earnings = pool.min_stake * pool.daily_rate
        days_to_break_even = gas_cost / daily_earnings if daily_earnings > 0 else float("inf")
        min_stake_for_1yr = gas_cost / (pool.effective_apy) if pool.effective_apy > 0 else float("inf")

        return {
            "pool": pool.name,
            "gas_cost": f"{gas_cost:.6f} ETH",
            "min_stake_daily_earnings": f"{daily_earnings:,.4f} {pool.token}",
            "days_to_cover_gas": f"{days_to_break_even:.0f}",
            "min_stake_for_1yr_return": f"{min_stake_for_1yr:,.2f} {pool.token}",
            "viable": "Yes" if days_to_break_even < 365 else "No",
        }

    def multi_year_projection(self, pool: StakingPool, principal: float, years: int) -> List[Dict]:
        projections = []
        for year in range(1, years + 1):
            days = year * 365
            result = self.calculate_rewards(pool, principal, days, compound=True)
            projections.append({
                "year": year,
                "balance": result["final_balance"],
                "cumulative_rewards": result["total_rewards"],
                "roi": result["roi"],
            })
        return projections


def main():
    import argparse
    parser = argparse.ArgumentParser(description="MiMo Staking Calculator")
    parser.add_argument("--principal", type=float, default=10000)
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--pool", help="Specific pool name")
    parser.add_argument("--compare", action="store_true")
    parser.add_argument("--projection", type=int, help="Multi-year projection")
    parser.add_argument("--break-even", type=float, help="Break-even analysis with gas cost")
    args = parser.parse_args()

    calc = StakingCalculator()
    pools = [
        StakingPool("ETH Staking", "Lido", "stETH", 0.035, 0.01, 0, 0, 0.10, True),
        StakingPool("ATOM Staking", "Cosmos Hub", "ATOM", 0.18, 1, 21, 21, 0.05, True),
        StakingPool("SOL Staking", "Marinade", "mSOL", 0.07, 0.1, 0, 3, 0.02, True),
        StakingPool("DOT Staking", "Polkadot", "DOT", 0.14, 10, 28, 28, 0.05, True),
        StakingPool("MATIC Staking", "Lido", "stMATIC", 0.045, 1, 0, 3, 0.10, True),
    ]
    for pool in pools:
        calc.add_pool(pool)

    if args.compare:
        results = calc.compare_pools(args.principal, args.days)
        print(f"\nComparison ({args.principal:,.0f} capital, {args.days} days):")
        for r in results:
            print(f"  {r['pool']}: {r['roi']} ROI | APY {r['effective_apy']}")
    elif args.pool:
        pool = next((p for p in pools if p.name.lower() == args.pool.lower()), None)
        if pool:
            result = calc.calculate_rewards(pool, args.principal, args.days)
            print(json.dumps(result, indent=2))
        else:
            print(f"Pool '{args.pool}' not found")
    elif args.projection:
        pool = pools[0]
        projections = calc.multi_year_projection(pool, args.principal, args.projection)
        print(f"\n{args.projection}-Year Projection for {pool.name}:")
        for p in projections:
            print(f"  Year {p['year']}: {p['balance']} (ROI: {p['roi']})")
    elif args.break_even:
        for pool in pools:
            result = calc.break_even_analysis(pool, args.break_even)
            print(f"  {pool.name}: {result['days_to_cover_gas']} days to cover gas ({result['viable']})")
    else:
        result = calc.calculate_rewards(pools[0], args.principal, args.days)
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
