# Fullstack QA Lab

Учебный QA-проект для портфолио: локальный сервис задач, UI/API-автоматизация и мониторинг. Создан с помощью AI; это не коммерческий проект и не подтверждение production-опыта. Тестируемая система намеренно небольшая, чтобы можно было проверить каждый сценарий и объяснить архитектуру.

## Стек

Python / FastAPI · JavaScript / Playwright Test · Pytest · REST API · SQLite / SQL · GitHub Actions · Docker Compose · Prometheus · Grafana.

## Быстрый запуск тестов

Нужны Python 3.12+ и Node.js 22+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
npm ci
npx playwright install --with-deps chromium
pytest -q
npm test
```

Playwright самостоятельно поднимает приложение на порту 8000. Освободите порт перед запуском. У каждого API-теста Pytest отдельная временная SQLite БД; браузерные тесты создают уникальные данные и удаляют их в finally. Не запускайте несколько независимых команд npm test одновременно с одной e2e.db.

## Приложение и мониторинг

```bash
docker compose up --build -d
curl http://localhost:8000/health
curl -X POST http://localhost:8000/api/tasks -H 'Content-Type: application/json' -d '{"title":"Explore metrics"}'
```

- UI: http://localhost:8000
- OpenAPI/Swagger UI: http://localhost:8000/docs
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 — дашборд **QA Lab — API Health** provisioned автоматически.

Дашборд показывает запросы в секунду, частоту HTTP 5xx и p95 задержки. Для rate нужны минимум два scrape; генерируйте запросы и подождите 15–30 секунд. Пустые графики без нагрузки нормальны. Label route использует шаблон `/api/tasks/{task_id}`, чтобы ID не создавали бесконечное число временных рядов. Метрики процесса хранятся в памяти; это конфигурация с одним worker.

Сервисы опубликованы только на loopback. Анонимный доступ Grafana разрешен только для чтения; стенд предназначен для локального обучения. В приложении нет авторизации и разграничения пользователей: не публикуйте его в интернет как production-сервис.

```bash
docker compose down
# Удаление данных задач, только если они больше не нужны:
docker compose down -v
```

## Что проверяем

| Уровень | Риски и сценарии |
| --- | --- |
| Pytest + FastAPI TestClient | CRUD, сохранение изменений, 404, пустые/невалидные значения, границы 1/120/121, Unicode, строгий boolean |
| SQL | Сверка записи API с БД, параметризованные запросы и SQL-подобный пользовательский ввод |
| Playwright UI | Создание, выполнение, сохранение после reload и удаление задачи |
| Playwright UI + API | Подготовка данных через API; HTML-подобный ввод отображается как текст |
| Playwright APIRequestContext | CRUD и негативная проверка REST API через реальный HTTP |
| Observability | Экспорт счетчиков/гистограмм и стабильные route labels |

Проверка SQL-подобного ввода и один XSS-сценарий не заменяют полноценный аудит безопасности. SQLite не подтверждает опыт PostgreSQL. TestClient не заменяет тесты на реальном HTTP — для этого есть Playwright API.

## CI и диагностика

GitHub Actions запускает Pytest и Chromium на push / pull_request. Загружает JUnit XML, HTML-отчет Playwright, trace и screenshot при падении. Артефакты хранятся 7 дней. Допускается один CI retry, чтобы видеть flaky-тесты в отчете; локально retries выключены.

```bash
npm run report
npx playwright show-trace test-results/<test-directory>/trace.zip
```

Если Playwright упал, сначала проверьте отчет, сетевые запросы и trace, затем сопоставьте симптом с API и БД. Процент покрытия кода и сокращение времени регресса здесь не измерены.

## Что разобрать перед собеседованием

1. Отличие изоляции данных в Pytest и Playwright, риски общих тестовых данных.
2. Почему используются role/label locators и assertions с auto-wait, а не sleep.
3. Как API fixtures ускоряют UI-сценарии; почему проверки UI и API не полностью дублируются.
4. Как различаются p95, средняя задержка и частота ошибок; как читается PromQL.
5. Почему retries могут скрывать нестабильность и как находить первопричину через trace.
6. Какие проверки добавить для настоящего продукта: авторизация, конкурентные изменения, пагинация, миграции, кроссбраузерность и нагрузочные профили.

## Границы проекта

Это небольшая демонстрация с Chromium, синхронной SQLite и одним экземпляром приложения. Здесь нет Kubernetes, Kafka, Redis, Allure, нагрузочного тестирования или промышленного управления секретами. Не указывайте их в резюме на основании этого репозитория.

## Проверка при подготовке проекта

- Pytest: 18 passed.
- Playwright Chromium: 3 passed.
- Docker image: успешно собран.
- `docker compose config -q`: успешно.
- Запуск полного monitoring-стенда не завершен: дисковый лимит среды при создании контейнера Grafana. Provisioning и отображение дашборда в работающей Grafana требуют проверки.
- GitHub Actions настроен, но удаленный запуск не проверен до публикации репозитория.
