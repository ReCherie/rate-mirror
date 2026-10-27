"""IRR 核心引擎：牛顿迭代解现金流内部收益率。

设计原则：数学全部由确定性代码完成，LLM 不参与任何计算。
口径：headline 年化利率 = 月 IRR × 12（名义年化，与监管"明示年化利率"常用口径一致）；
     同时给出有效年化 (1+r)^12 - 1 供对照。
"""
from __future__ import annotations


def irr_monthly(cashflows: list[float], guess: float = 0.02) -> float:
    """解方程 sum(cf_t / (1+r)^t) = 0，t=0..n，cashflows[0] 为负（放款）。

    牛顿迭代，不收敛时自动退回二分法（r 在 [1e-9, 2.0] 之间必有唯一解，
    因为放款为负、后续现金流均为正）。
    """
    if not cashflows or cashflows[0] >= 0:
        raise ValueError("现金流首项必须为负值（放款金额）")
    if not any(cf > 0 for cf in cashflows[1:]):
        raise ValueError("后续现金流必须存在正数（还款金额）")

    # --- 牛顿迭代 ---
    r = guess
    for _ in range(100):
        f = sum(cf / (1 + r) ** t for t, cf in enumerate(cashflows))
        df = sum(t * cf / (1 + r) ** (t + 1) for t, cf in enumerate(cashflows))
        if abs(f) < 1e-10:
            return r
        if df == 0:
            break
        r_new = r - f / df
        if r_new <= 0 or r_new > 10:  # 越界则放弃牛顿，转二分
            break
        r = r_new
        if abs(f) < 1e-10:
            return r

    # --- 二分法兜底 ---
    lo, hi = 1e-9, 2.0

    def f(r: float) -> float:
        return sum(cf / (1 + r) ** t for t, cf in enumerate(cashflows))

    if f(lo) * f(hi) > 0:
        raise ValueError("现金流无解，请检查输入")
    for _ in range(200):
        mid = (lo + hi) / 2
        if f(mid) > 0:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-10:
            break
    return (lo + hi) / 2


def annualized(monthly: float) -> tuple[float, float]:
    """返回 (名义年化 APR = 月IRR*12, 有效年化 EAR = (1+r)^12 - 1)。"""
    return monthly * 12, (1 + monthly) ** 12 - 1


def pv(cashflows: list[float], r: float) -> float:
    """给定利率下的现金流现值（用于单元测试与双重校验）。"""
    return sum(cf / (1 + r) ** t for t, cf in enumerate(cashflows))


def parse_bill_to_cashflows(principal: float, payments: list[float],
                            upfront_fee: float = 0.0) -> list[float]:
    """组装现金流：[-(principal - upfront_fee), *payments]。

    一次性 upfront 服务费/手续费会减少实际到手金额，从而抬高真实利率
    ——这正是"费率美化"的经典手法，必须计入。
    """
    return [-(principal - upfront_fee)] + list(payments)


def total_interest(principal: float, payments: list[float], upfront_fee: float = 0.0) -> float:
    """总成本 = 还款总额 + 前置费用 - 本金。"""
    return sum(payments) + upfront_fee - principal
