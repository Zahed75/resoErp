# Part of Odoo. See LICENSE file for full copyright and licensing details.
import re
from typing import NamedTuple

from odoo.api import Environment
from odoo.exceptions import UserError


class Provider(NamedTuple):
    name: str
    display_name: str
    embedding_model: str
    embedding_config: dict
    llms: list[tuple[str, str]]
    deprecated_models: list[str]
    response_style_to_llm_model_and_reasoning: dict[str, tuple[str, str]]


PROVIDERS = [
    Provider(
        "openai",
        "OpenAI",
        "text-embedding-3-small",
        {
            # https://platform.openai.com/docs/api-reference/embeddings/create
            "max_batch_size": 2048,
            "max_tokens_per_request": 200000,
        },
        [
            ("gpt-4", "ChatGPT (Auto)"),
            ("gpt-4o", "GPT-4o"),
            ("gpt-4.1", "GPT-4.1"),
            ("gpt-4.1-mini", "GPT-4.1 Mini"),
            ("gpt-5", "GPT-5"),
            ("gpt-5-mini", "GPT-5 Mini"),
        ],
        ["gpt-3.5-turbo", "gpt-4"],
        {
            "analytical": ("gpt-5.6-terra", "medium"),
            "balanced": ("gpt-5.6-terra", "low"),
            "creative": ("gpt-5.6-luna", "low"),
        },
    ),
    Provider(
        "google",
        "Google",
        "gemini-embedding-2",
        {
            # https://googleapis.dev/python/generativelanguage/latest/_modules/google/ai/generativelanguage_v1alpha/types/text_service.html#BatchEmbedTextRequest
            "max_batch_size": 100,
            "max_tokens_per_request": 10000,
        },
        [
            ("gemini-1.5-flash", "Gemini (Auto)")
        ],
        [
            "gemini-1.5-pro", "gemini-1.5-flash", "gemini-embedding-001",
            "gemini-2.5-pro", "gemini-2.5-flash",
        ],
        {
            "analytical": ("gemini-3-flash-preview", "medium"),
            "balanced": ("gemini-3-flash-preview", "low"),
            "creative": ("gemini-3.1-flash-lite", "minimal"),
        },
    ),
]

DEPRECATED_MODELS = [model for provider in PROVIDERS for model in provider.deprecated_models]

EMBEDDING_MODELS_SELECTION = [
    (provider.embedding_model, provider.display_name) for provider in PROVIDERS
]

TEMPERATURE_MAP = {
    'analytical': 0.2,
    'balanced': 0.5,
    'creative': 0.8,
}


def get_provider_for_embedding_model(env, embedding_model):
    for p in PROVIDERS:
        if p.embedding_model == embedding_model or embedding_model in p.deprecated_models:
            return p.name
    raise UserError(env._("No provider found for the embedding model"))


def get_provider(env, llm_model):
    for p in PROVIDERS:
        if llm_model in [m[0] for m in p.llms] + p.deprecated_models:
            return p.name
    raise UserError(env._("No provider found for the selected model"))


def get_embedding_config(env, provider):
    for p in PROVIDERS:
        if p.name == provider:
            return p.embedding_config
    raise UserError(env._("No embedding configuration found for the provider"))


def get_llm_model_and_reasoning(llm_model: str, temperature: float) -> tuple[str, str | None]:
    response_style = next((style for style, temp in TEMPERATURE_MAP.items() if temp == temperature), 'balanced')

    for provider in PROVIDERS:
        if llm_model in provider.deprecated_models:
            return provider.response_style_to_llm_model_and_reasoning[response_style]

    reasoning = None
    if llm_model in ('gpt-5', 'gpt-5-mini'):
        response_style_to_reasoning = {"analytical": "medium", "balanced": "low", "creative": "minimal"}
        reasoning = response_style_to_reasoning[response_style]
    return llm_model, reasoning


def get_deprecated_model_replacement_label(llm_model: str, response_style: str) -> str | None:\

    def format_model_name(model_name: str) -> str:
        # gpt-5.6-luna -> GPT 5.6 Luna, gemini-3-flash-preview -> Gemini 3 Flash
        suffixes_to_remove = ["-preview"]
        name_parts = re.sub(rf"(?:{'|'.join(suffixes_to_remove)})$", "", model_name).split("-")
        return " ".join(p.upper() if p.lower() == "gpt" else p.capitalize() for p in name_parts)

    for provider in PROVIDERS:
        if llm_model in provider.deprecated_models:
            model_replacing_deprecated, reasoning = provider.response_style_to_llm_model_and_reasoning[response_style]
            return f"{format_model_name(model_replacing_deprecated)} {reasoning} thinking"
    return None


def check_model_depreciation(env: Environment, model: str) -> None:
    if model in DEPRECATED_MODELS:
        raise UserError(env._("%s is no longer available. Please select a newer model.", model))


def get_embedding_model(provider_name: str):
    for provider in PROVIDERS:
        if provider.name == provider_name:
            return provider.embedding_model
