"""报告生成与花式换算模块。"""
from __future__ import annotations

from . import irr as _irr


def analyze(principal: float, payments: list[float], upfront_fee: float = 0.0,
            nominal_rate_text: str = "", monthly_salary: float = 8000.0) -> dict:
    """主分析函数：输入账单结构，输出完整报告 dict。"""
    cashflows = _irr.parse_bill_to_cashflows(principal, payments, upfront_fee)
    r_m = _irr.irr_monthly(cashflows)
    apr, ear = _irr.annualized(r_m)
    cost = _irr.total_interest(principal, payments, upfront_fee)

    return {
        "principal": principal,
        "upfront_fee": upfront_fee,
        "total_paid": sum(payments) + upfront_fee,
        "total_cost": cost,
        "monthly_irr": r_m,
        "apr": apr,                # headline：名义年化（月IRR×12）
        "ear": ear,                # 有效年化（复利口径）
        "nominal_rate_text": nominal_rate_text,
        "milk_tea_cups": cost / 15.0,               # 一杯奶茶 15 元
        "salary_days": cost / (monthly_salary / 21.75),  # 按月薪折算工作天数
        "cashflows": cashflows,
    }


def redline_verdict(apr: float, four_x_lpr: float = 12.0) -> dict:
    """司法红线判定。four_x_lpr = 1年期LPR×4，需按最新 LPR 自行更新。"""
    exceeded = apr > four_x_lpr
    return {
        "exceeded": exceeded,
        "limit": four_x_lpr,
        "message": (f"⚠️ 实际年化 {apr:.2%} 已超过司法保护上限（4倍LPR ≈ {four_x_lpr:.0%}）"
                    if exceeded else
                    f"✅ 实际年化 {apr:.2%} 未超过司法保护上限（4倍LPR ≈ {four_x_lpr:.0%}）"),
    }


def prepay_decision(remaining_periods: int, monthly_payment: float,
                    remaining_principal: float, penalty: float = 0.0) -> dict:
    """提前还款决策：比较（剩余利息总额）与（违约金）。

    简化口径：剩余利息 = 剩余还款总额 - 剩余本金。
    若违约金 >= 剩余利息 → 提前还款不划算；否则划算。
    """
    remaining_total = monthly_payment * remaining_periods
    remaining_interest = remaining_total - remaining_principal
    if remaining_interest < 0:
        remaining_interest = 0.0
    if penalty >= remaining_interest:
        verdict = "不划算", f"违约金 {penalty:,.0f} 元 ≥ 剩余利息 {remaining_interest:,.0f} 元，提前还款省不了钱。"
    else:
        verdict = "划算", (f"剩余利息 {remaining_interest:,.0f} 元 > 违约金 {penalty:,.0f} 元，"
                        f"提前还款约省 {remaining_interest - penalty:,.0f} 元。")
    return {
        "remaining_interest": remaining_interest,
        "penalty": penalty,
        "verdict": verdict[0],
        "message": verdict[1],
    }


def fany_conversion(cost: float, monthly_salary: float = 8000.0) -> str:
    """花式换算文案（现场演示的记忆点）。"""
    cups = cost / 15.0
    days = cost / (monthly_salary / 21.75)
    if cups >= 1:
        return f"这笔利息 ≈ {cups:.0f} 杯奶茶，或你 {days:.1f} 天的工资。"
    return f"这笔利息 ≈ {cost:.0f} 元，看起来不多，但年化看就清楚了。"
