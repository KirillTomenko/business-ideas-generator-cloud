import os
import json
from typing import List, Optional

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from openai import OpenAI


PROXY_API_URL = os.getenv("PROXY_API_URL")
PROXY_API_KEY = os.getenv("PROXY_API_KEY")

client = None
if PROXY_API_KEY and PROXY_API_URL:
    client = OpenAI(
        api_key=PROXY_API_KEY,
        base_url=PROXY_API_URL.rstrip("/"),
    )


class StepPlan(BaseModel):
    title: str
    prompt: str


class GenerateRequest(BaseModel):
    niche: str
    region: Optional[str] = None


class StepLog(BaseModel):
    step_index: int
    step_title: str
    prompt_sent: str
    response_summary: str


class GenerateResponse(BaseModel):
    logs: List[StepLog]
    final_report: str


app = FastAPI(title="Генератор бизнес-идей")

templates = Jinja2Templates(directory="frontend/templates")
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


async def call_chat(messages: List[dict], response_format: Optional[dict] = None) -> str:
    if client is None:
        # Fallback для случая, когда прокси ещё не настроен
        return "Proxy API не настроен (отсутствуют PROXY_API_URL / PROXY_API_KEY)."

    kwargs = {
        "model": "gpt-4.1-mini",
        "messages": messages,
    }
    if response_format is not None:
        kwargs["response_format"] = response_format

    completion = client.chat.completions.create(**kwargs)
    return completion.choices[0].message.content or ""


async def get_research_plan(niche: str, region: Optional[str]) -> List[StepPlan]:
    system_prompt = (
        "Ты эксперт по исследованию рынков и генерации бизнес-идей.\n"
        "Составь пошаговый план (5-7 шагов) для исследования рынка в нише, "
        "указанной пользователем, и генерации 3-5 бизнес-идей.\n"
        "План должен включать: анализ трендов, изучение конкурентов, "
        "выявление болей аудитории, поиск незанятых ниш, генерацию идей.\n"
        "Верни результат в JSON-массиве, каждый элемент — объект со свойствами "
        "\"title\" (краткое название шага) и \"prompt\" (подробный промпт для ChatGPT, "
        "что именно искать/анализировать). Никакого текста вне JSON."
    )

    user_prompt = f"Ниша: {niche}."
    if region:
        user_prompt += f" Регион/рынок: {region}."

    content = await call_chat(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    )

    # Попробуем распарсить JSON из ответа
    try:
        data = json.loads(content)
        steps = [StepPlan(**item) for item in data]
        return steps
    except Exception:
        # Если модель вернула невалидный JSON, обернём в один шаг
        return [
            StepPlan(
                title="Общий анализ ниши",
                prompt=(
                    "На основе своей экспертизы выполни анализ рынка по нише: "
                    f"{niche}. Регион: {region or 'глобальный'}. "
                    "Опиши тренды, конкурентов, боли аудитории, возможности и идеи."
                ),
            )
        ]


async def run_research_steps(
    steps: List[StepPlan], niche: str, region: Optional[str]
) -> List[StepLog]:
    logs: List[StepLog] = []

    for idx, step in enumerate(steps, start=1):
        # Здесь можно было бы добавлять реальные результаты веб-поиска, если они есть.
        enriched_prompt = (
            f"Ниша: {niche}. Регион: {region or 'глобальный'}.\n"
            f"{step.prompt}\n"
            "Если у тебя есть доступ к актуальному веб-поиску — используй его. "
            "Если нет — опирайся на свою обученную модель и знания."
        )

        response = await call_chat(
            messages=[
                {
                    "role": "system",
                    "content": "Ты аналитик рынка. Кратко, структурированно подводи итоги шага.",
                },
                {"role": "user", "content": enriched_prompt},
            ]
        )

        logs.append(
            StepLog(
                step_index=idx,
                step_title=step.title,
                prompt_sent=enriched_prompt,
                response_summary=response,
            )
        )

    return logs


async def build_final_report(logs: List[StepLog], niche: str, region: Optional[str]) -> str:
    summary_parts = [
        f"Шаг {log.step_index} - {log.step_title}:\n{log.response_summary}"
        for log in logs
    ]
    combined_summary = "\n\n".join(summary_parts)

    final_prompt = (
        "На основе приведённых результатов шагов исследования рынка по нише "
        f"\"{niche}\" (регион: {region or 'глобальный'}):\n\n"
        f"{combined_summary}\n\n"
        "Сформируй структурированный отчёт с 3-5 бизнес-идеями. Для каждой идеи укажи:\n"
        "- название;\n"
        "- краткое описание;\n"
        "- целевая аудитория;\n"
        "- конкурентные преимущества;\n"
        "- ключевые риски и ограничения.\n"
        "Верни результат в удобном для чтения формате (подзаголовки, списки)."
    )

    report = await call_chat(
        messages=[
            {"role": "system", "content": "Ты бизнес-аналитик и генератор бизнес-идей."},
            {"role": "user", "content": final_prompt},
        ]
    )
    return report


@app.post("/api/generate", response_model=GenerateResponse)
async def generate_ideas(payload: GenerateRequest):
    if not payload.niche.strip():
        return JSONResponse(
            status_code=400,
            content={"detail": "Ниша не должна быть пустой"},
        )

    steps = await get_research_plan(payload.niche, payload.region)
    logs = await run_research_steps(steps, payload.niche, payload.region)
    final_report = await build_final_report(logs, payload.niche, payload.region)

    return GenerateResponse(logs=logs, final_report=final_report)

