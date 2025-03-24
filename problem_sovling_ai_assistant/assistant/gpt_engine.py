import openai
import logging
import json
import re
import os
from dotenv import load_dotenv
from openai import OpenAI

# Загружаем переменные окружения
load_dotenv()

logger = logging.getLogger(__name__)
client = OpenAI()

# ID ассистента из .env
ASSISTANT_ID = os.getenv("OPENAI_ASSISTANT_ID")

if not ASSISTANT_ID:
    raise ValueError("❗ Не указан OPENAI_ASSISTANT_ID в .env")

# Регулярка для валидации ключевого вопроса
QUESTION_PATTERN = re.compile(
    r"Что( именно)? следует сделать [^,]+, чтобы (перейти от [^ ]+ к [^ ]+|понять [^?]+)\??", re.IGNORECASE
)

def validate_key_question_format(text: str) -> bool:
    """
    Проверяет, соответствует ли ключевой вопрос одному из допустимых шаблонов.
    """
    if not text:
        return False
    return bool(QUESTION_PATTERN.search(text.strip()))

def try_extract_json(text: str):
    """
    Пытается извлечь JSON из текста ответа GPT.
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'{.*}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                logger.warning("❗ Не удалось распарсить вложенный JSON-блок")
    logger.warning("⚠️ Ответ не является корректным JSON. Возвращаем как есть.")
    return {"analysis": text, "key_question": "", "field_comments": {}}

def ask_gpt_with_validation(problem_data: dict) -> dict:
    logger.debug("🧼 Старт валидации данных GPT-ассистентом")

    message = f"""
Ты — эксперт по проблемному мышлению. Проанализируй следующие поля карточки проблемы и предложи ключевой вопрос по шаблону «Что следует сделать X, чтобы перейти от R1 к R2?» или по одному из 7 шаблонов Барбары Минто.

Вот входные данные:

Кто: {problem_data.get('who')}
Что: {problem_data.get('what')}
Где: {problem_data.get('where')}
Когда: {problem_data.get('when')}
Почему сейчас: {problem_data.get('why_now')}
R1: {problem_data.get('r1_as_is')}
R2: {problem_data.get('r2_to_be')}
Gap: {problem_data.get('gap')}
Тип проблемы: {problem_data.get('problem_type')}

Верни ответ в формате JSON строго по этой схеме:
{{
  "analysis": "Анализ проблемы на основе R1, R2, GAP",
  "key_question": "Корректно сформулированный ключевой вопрос",
  "field_comments": {{
    "who": "Комментарий к полю 'Кто', если требуется уточнение",
    "what": "...",
    "where": "...",
    "when": "...",
    "why_now": "...",
    "r1_as_is": "...",
    "r2_to_be": "...",
    "gap": "...",
    "problem_type": "..."
  }}
}}
"""

    logger.info("🤖 Отправляем данные на анализ GPT")
    thread = client.beta.threads.create()
    thread_id = thread.id
    logger.info(f"🧵 Thread создан: {thread_id}")

    client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=message
    )

    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=ASSISTANT_ID,
    )

    logger.info(f"▶️ Assistant run начат: {run.id}")

    # Ждем завершения
    while True:
        run_status = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
        if run_status.status in ["completed", "failed", "cancelled", "expired"]:
            break

    if run_status.status != "completed":
        logger.warning(f"⛔ Ассистент завершился со статусом: {run_status.status}")
        return {"analysis": "Ошибка при обработке GPT", "key_question": "", "field_comments": {}}

    messages = client.beta.threads.messages.list(thread_id=thread_id)
    content = ""

    for message in reversed(messages.data):
        if message.role == "assistant":
            if message.content and message.content[0].type == "text":
                content = message.content[0].text.value
                break

    logger.debug(f"📬 Ответ GPT: {content}")
    return try_extract_json(content)
