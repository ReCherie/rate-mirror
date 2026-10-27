"""LLM 账单解析模块：DeepSeek Function Calling 结构化抽取。

架构原则：LLM 只负责"读懂账单文本并抽取字段"，绝不参与利率计算。
未配置 API Key 时抛出友好提示，Demo 退回手动录入模式。
"""
from __future__ import annotations

import json
import os

PARSE_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "parse_bill",
        "description": "从分期账单/贷款合同文本中抽取结构化字段",
        "parameters": {
            "type": "object",
            "properties": {
                "principal": {"type": "number", "description": "借款本金（元）"},
                "periods": {"type": "integer", "description": "还款期数（月）"},
                "installments": {
                    "type": "array", "items": {"type": "number"},
                    "description": "每期还款额（元），含本金+利息+所有按期费用"
                },
                "nominal_rate": {"type": "string",
                                 "description": "商家标称费率原文，如 '0.6%/月'、'日息万五'、'免息'"},
                "upfront_fee": {"type": "number",
                                "description": "一次性前置费用合计（元），如服务费/手续费/担保费；无则为0"},
                "fee_names": {"type": "array", "items": {"type": "string"},
                              "description": "识别出的附加费用名称列表"},
                "prepay_penalty": {"type": "number",
                                   "description": "提前还款违约金条款（元），未提及则为0"}
            },
            "required": ["principal", "periods", "installments", "nominal_rate"]
        }
    }
}

SYSTEM_PROMPT = """你是一个账单结构化助手。你的任务是从用户粘贴的分期账单文本中抽取字段，
通过 parse_bill 工具输出。注意：
1. 服务费、担保费、手续费、保险费等任何附加费用都必须识别，绝不能遗漏（它们是利率美化的常见手段）；
2. 你不需要做任何数学计算，利率由下游确定性代码计算；
3. 若文本信息不足，将缺失字段置为 0 或空，不要编造数值。"""


def normalize_installments(fields: dict) -> list[float]:
    """归一化每期还款额数组。

    LLM 常见输出偏差：把等额还款抽成单元素数组 [1072] 而非 12 个元素。
    这里按 periods 补齐：单元素→复制 periods 份；不足→用最后一期补齐。
    """
    inst = [float(x) for x in (fields.get("installments") or [])]
    periods = int(fields.get("periods") or len(inst) or 0)
    if not inst:
        raise ValueError("未识别到每期还款额（installments 为空）")
    if periods <= 0:
        raise ValueError("未识别到期数（periods）")
    if len(inst) == 1 and periods > 1:
        inst = inst * periods
    elif len(inst) < periods:
        inst = inst + [inst[-1]] * (periods - len(inst))
    elif len(inst) > periods:      # 多抽了则按 periods 截断
        inst = inst[:periods]
    return inst


def parse_bill_text(text: str) -> dict:
    """调用 DeepSeek 抽取账单字段，返回 dict。无 API Key 时抛 RuntimeError。"""
    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "未配置 DEEPSEEK_API_KEY。请在启动前 `export DEEPSEEK_API_KEY=sk-...`，"
            "或改用「手动录入 / 示例账单」模式。"
        )
    from openai import OpenAI  # 延迟导入，避免未装依赖时手动模式不可用
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        tools=[PARSE_TOOL_SCHEMA],
        tool_choice={"type": "function", "function": {"name": "parse_bill"}},
        temperature=0,
    )
    return json.loads(resp.choices[0].message.tool_calls[0].function.arguments)
