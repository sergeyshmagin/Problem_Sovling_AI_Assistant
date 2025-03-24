import openai
import logging
import json
import re
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
logger = logging.getLogger(__name__)
client = OpenAI()

ASSISTANT_ID = os.getenv("OPENAI_ASSISTANT_ID")
if not ASSISTANT_ID:
    raise ValueError("❗ Не указан OPENAI_ASSISTANT_ID в .env")

# Шаблон ключевого вопроса
QUESTION_PATTERN = re.compile(
    r"Что( именно)? следует сделать [^,]+, чтобы (перейти от [^ ]+ к [^ ]+|понять [^?]+)\??",
    re.IGNORECASE
)

def validate_key_question_format(text: str) -> bool:
    if not text:
        return False
    return bool(QUESTION_PATTERN.search(text.strip()))

def try_extract_json(text: str):
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

    # Автоматическая логическая проверка (например, числовые значения для GAP)
    r1 = problem_data.get("r1_as_is", "")
    r2 = problem_data.get("r2_to_be", "")
    gap = problem_data.get("gap", "")

    numbers_r1 = list(re.findall(r'\d+', r1))
    numbers_r2 = list(re.findall(r'\d+', r2))
    if gap and (not numbers_r1 or not numbers_r2):
        return {
            "analysis": "GAP указан, но в R1 или R2 отсутствуют числовые значения, на основе которых можно посчитать разрыв.",
            "key_question": "",
            "field_comments": {
                "gap": "Невозможно оценить GAP без числовых значений в R1 и R2. Уточните: укажите, например, '15 дней' и '7 дней'."
            }
        }

    message = f"""
Ты — ассистент по проблемному мышлению. Проанализируй поля карточки проблемы. 

🔍 Дай дидактичные комментарии, объясняющие, **почему** формулировка может быть некорректной — с отсылкой к критериям SMART, MECE, логике R1-R2-GAP.

✅ Если поле корректно, просто скажи, что всё хорошо.

📌 Если есть недочёты, предложи **конкретные улучшения**. Не пиши просто "размыто" — уточни, что именно улучшить. Например: "Уточните результат: вместо 'улучшить показатели' — 'увеличить экспорт с 5 до 10 млн долларов'".

⚠️ Если хотя бы одно поле некорректно — **не переходи к формулировке ключевого вопроса**. Верни пустую строку в key_question.

Формат ответа — строго JSON:
{{
  "analysis": "Общий анализ связности R1, R2, GAP и качества описания",
  "key_question": "Формулировка ключевого вопроса ИЛИ пусто, если поля некорректны",
  "field_comments": {{
    "who": "...",
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

Данные пользователя:

Кто: {problem_data.get('who')}
Что: {problem_data.get('what')}
Где: {problem_data.get('where')}
Когда: {problem_data.get('when')}
Почему сейчас: {problem_data.get('why_now')}
R1: {r1}
R2: {r2}
Gap: {gap}
Тип проблемы: {problem_data.get('problem_type')}
"""

    logger.info("🤖 Отправляем данные на анализ GPT")
    thread = client.beta.threads.create()
    thread_id = thread.id

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
        if message.role == "assistant" and message.content and message.content[0].type == "text":
            content = message.content[0].text.value
            break

    logger.debug(f"📬 Ответ GPT: {content}")
    parsed = try_extract_json(content)

    # Дополнительная валидация ключевого вопроса
    if parsed.get("key_question") and not validate_key_question_format(parsed["key_question"]):
        logger.info("⚠️ Ключевой вопрос не соответствует шаблону. Обнуляем.")
        parsed["key_question"] = ""

    return parsed
