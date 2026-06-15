#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AI 模型接入预设。"""

from copy import deepcopy
from typing import Any, Dict, List


AI_ACCESS_MODES: Dict[str, str] = {
    "coding_plan": "模型 Coding Plan",
    "api": "模型 API",
    "custom": "自定义模型",
}


AI_PROVIDER_PRESETS: Dict[str, List[Dict[str, Any]]] = {
    "coding_plan": [
        {
            "id": "tencent_token_plan_personal",
            "name": "腾讯云 Token Plan（个人版）",
            "base_url": "https://api.lkeap.cloud.tencent.com/plan/v3",
            "models": ["需手动填写"],
        },
        {
            "id": "tencent_token_plan_enterprise",
            "name": "腾讯云 Token Plan（企业版）",
            "base_url": "https://tokenhub.tencentmaas.com/plan/v3",
            "models": ["需手动填写"],
        },
        {
            "id": "minimax_token_plan_cn",
            "name": "MiniMax Token Plan（国内）",
            "base_url": "https://api.minimaxi.com/v1",
            "models": ["MiniMax-Text-01", "需手动填写"],
            "anthropic_url": "https://api.minimaxi.com/anthropic",
        },
        {
            "id": "glm_coding_plan_cn",
            "name": "智谱 GLM Coding Plan（国内）",
            "base_url": "https://open.bigmodel.cn/api/coding/paas/v4",
            "models": ["glm-4-flash", "glm-4-plus", "glm-4-air", "需手动填写"],
            "anthropic_url": "https://open.bigmodel.cn/api/anthropic",
        },
        {
            "id": "kimi_coding_plan",
            "name": "Kimi Coding Plan",
            "base_url": "https://api.kimi.com/coding/v1",
            "models": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k", "需手动填写"],
            "anthropic_url": "https://api.kimi.com/coding/",
        },
        {
            "id": "xiaomi_token_plan",
            "name": "小米 Token Plan",
            "base_url": "https://token-plan-cn.xiaomimimo.com/v1",
            "models": ["需手动填写"],
            "anthropic_url": "https://token-plan-cn.xiaomimimo.com/anthropic",
        },
        {
            "id": "baidu_coding_plan",
            "name": "百度 Coding Plan",
            "base_url": "",
            "models": ["需手动填写"],
        },
        {
            "id": "volcengine_ark_coding_plan",
            "name": "火山引擎方舟 Coding Plan",
            "base_url": "https://ark.cn-beijing.volces.com/api/coding/v3",
            "models": ["需填写方舟 Endpoint ID"],
            "anthropic_url": "https://ark.cn-beijing.volces.com/api/coding",
        },
        {
            "id": "tencent_coding_plan",
            "name": "腾讯云 Coding Plan",
            "base_url": "https://api.lkeap.cloud.tencent.com/coding/v3",
            "models": ["需手动填写"],
        },
        {
            "id": "custom_coding_plan",
            "name": "自定义 Coding Plan",
            "base_url": "",
            "models": ["自定义模型"],
        },
    ],
    "api": [
        {
            "id": "tencent_tokenhub",
            "name": "腾讯云 TokenHub",
            "base_url": "",
            "models": ["需手动填写"],
        },
        {
            "id": "deepseek",
            "name": "DeepSeek",
            "base_url": "https://api.deepseek.com",
            "models": ["deepseek-chat", "deepseek-reasoner"],
        },
        {
            "id": "alibaba_bailian",
            "name": "百炼 / 千问",
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "models": ["qwen-plus", "qwen-turbo", "qwen-max"],
        },
        {
            "id": "minimax",
            "name": "MiniMax",
            "base_url": "https://api.minimax.chat/v1",
            "models": ["MiniMax-Text-01"],
        },
        {
            "id": "kimi",
            "name": "Moonshot AI / Kimi",
            "base_url": "https://api.moonshot.cn/v1",
            "models": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
        },
        {
            "id": "glm",
            "name": "智谱 AI / GLM",
            "base_url": "https://open.bigmodel.cn/api/paas/v4",
            "models": ["glm-4-flash", "glm-4-plus", "glm-4-air"],
        },
        {
            "id": "volcengine_doubao",
            "name": "火山引擎 / 豆包",
            "base_url": "https://ark.cn-beijing.volces.com/api/v3",
            "models": ["需填写方舟 Endpoint ID"],
        },
        {
            "id": "xiaomi_mimo",
            "name": "小米 MiMo",
            "base_url": "",
            "models": ["需手动填写"],
        },
        {
            "id": "baidu_wenxin",
            "name": "百度 / 文心一言",
            "base_url": "",
            "models": ["需手动填写"],
        },
        {
            "id": "openai",
            "name": "OpenAI GPT",
            "base_url": "https://api.openai.com/v1",
            "models": ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini"],
        },
        {
            "id": "gemini",
            "name": "Google Gemini",
            "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
            "models": ["gemini-2.0-flash", "gemini-1.5-pro"],
        },
        {
            "id": "custom_api",
            "name": "自定义 API",
            "base_url": "",
            "models": ["自定义模型"],
        },
    ],
    "custom": [
        {
            "id": "custom_openai",
            "name": "OpenAI 兼容",
            "base_url": "",
            "models": ["自定义模型"],
        },
    ],
}


def get_default_ai_settings() -> Dict[str, Any]:
    """返回默认 AI 设置。"""
    return {
        "enabled": False,
        "access_mode": "api",
        "provider": "deepseek",
        "provider_name": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
        "api_key": "",
        "timeout": 60,
        "temperature": 0.2,
        "max_tokens": 2000,
    }


def get_access_mode_names() -> List[str]:
    """返回接入方式显示名。"""
    return list(AI_ACCESS_MODES.values())


def mode_key_from_name(name: str) -> str:
    """根据显示名返回接入方式标识。"""
    for key, label in AI_ACCESS_MODES.items():
        if label == name:
            return key
    return name if name in AI_ACCESS_MODES else "api"


def mode_name_from_key(key: str) -> str:
    """根据接入方式标识返回显示名。"""
    return AI_ACCESS_MODES.get(key, AI_ACCESS_MODES["api"])


def get_providers(access_mode: str) -> List[Dict[str, Any]]:
    """返回接入方式下的服务商列表。"""
    return deepcopy(AI_PROVIDER_PRESETS.get(access_mode, AI_PROVIDER_PRESETS["api"]))


def get_provider(access_mode: str, provider_id: str) -> Dict[str, Any]:
    """返回指定服务商预设。"""
    providers = get_providers(access_mode)
    for provider in providers:
        if provider["id"] == provider_id:
            return provider
    return providers[0]


def provider_id_from_name(access_mode: str, name: str) -> str:
    """根据服务商显示名返回服务商标识。"""
    for provider in get_providers(access_mode):
        if provider["name"] == name:
            return provider["id"]
    return get_providers(access_mode)[0]["id"]


def provider_name_from_id(access_mode: str, provider_id: str) -> str:
    """根据服务商标识返回显示名。"""
    return get_provider(access_mode, provider_id)["name"]
