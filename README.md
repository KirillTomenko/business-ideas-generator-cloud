## Генератор бизнес-идей (VCc03)

Мини-приложение с псевдоагентом для исследования рынка и генерации бизнес-идей:

- **Backend**: `FastAPI` + `openai` (через Proxy API с кастомным `base_url`)
- **Frontend**: минималистичный HTML+CSS+JS (через Jinja2-шаблон)
- **Сборка**: `Docker` + `docker-compose`

### Настройка окружения

Создайте в корне проекта файл `.env`:

```env
PROXY_API_URL=https://ВАШ_PROXY_URL/v1
PROXY_API_KEY=ВАШ_API_КЛЮЧ
```

Важно: `PROXY_API_URL` должен указывать на совместимый с OpenAI Proxy API (поддержка `chat.completions.create`).

### Запуск через Docker Compose

В корне проекта выполните:

```bash
docker compose build
docker compose up
```

После успешного запуска backend будет доступен на `http://localhost:8000/`.

- Главная страница с формой: `http://localhost:8000/`
- API endpoint для генерации: `POST /api/generate`

### Ручной (локальный) запуск без Docker

Убедитесь, что установлен Python 3.11+.

```bash
pip install -r requirements.txt
set PROXY_API_URL=...
set PROXY_API_KEY=...
uvicorn backend.main:app --reload
```

На Windows переменные окружения можно задать через PowerShell:

```powershell
$env:PROXY_API_URL="https://..."
$env:PROXY_API_KEY="..."
uvicorn backend.main:app --reload
```

### Как это работает

1. Пользователь вводит **нишу/отрасль** и опционально **регион/рынок**.
2. Backend отправляет системный промпт в модель, запрашивая **план исследования (5–7 шагов) в JSON**.
3. Для каждого шага формируется промпт (может быть дополнен реальными данными, если Proxy поддерживает веб-поиск).
4. Результаты по шагам собираются как **лог**.
5. Все промежуточные результаты отправляются в модель для построения **финального отчёта с 3–5 бизнес-идеями**.
6. Frontend:
   - Псевдо-реально показывает выполнение шагов (выводит лог по одному шагу);
   - Отображает финальный отчёт;
   - Позволяет скачать результат в формате **Markdown**.

