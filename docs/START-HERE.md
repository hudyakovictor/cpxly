# Capexly: единый исходный кандидат, перенос на macOS

## Статус
Это полный снимок исходников кандидата после инфраструктуры, каталога, selfservice S-03 и reliability v2. Не требуется накладывать прежние ZIP/diff друг на друга. Это НЕ проверенный release image, не копия вашего рабочего репозитория и не резервная копия данных. Сервер не запущен. Исходная основа: saaspegasus/django-boilerplate, commit e9d11b0a294191af87fec6f84acb4d96454957be.

Работали только в отдельном кандидате. Путь /Users/victorkhudyakov/cpxly с этой Linux-машины недоступен и не изменялся. Если там уже есть проект, НЕ распаковывать поверх него: сначала отдельная staging-папка и сопоставление с вашим Git. В архиве нет .git, .env, ключей, volumes, backups, node_modules или .venv. Upstream editor/MCP-конфигурации .claude/.mcp.json также не включены. Реальные клиентские документы пока запрещены.

## Что подготовлено
- Django 6 starter, штатные allauth/templates/HTMX/daisyUI сохранены; новый frontend не вводится.
- Docker development/production stages; base/dev/prod/prod-test Compose; Caddy и вариант внешнего CA; non-root app; отдельные PostgreSQL runtime/migrator роли; секреты через runtime files; healthchecks/лимиты/постоянные тома.
- Garage вместо MinIO в dev; DEV-ONLY исключение GARAGE_ALLOW_WORLD_READABLE_SECRETS для file secrets 0444; оно не добавлено в prod/prod-test.
- Исправлены CASE guard has_sequence_privilege в check-runtime.sql и import path storage-smoke.py.
- Скрипты backup/restore, release build/save/load, image pins/digests, CI-конфигурация и инструкции.
- Каталог: 57 записей исследования, включая клиентские услуги, платформенные функции и GTM-гипотезы; не все являются услугами. В стандартной админке, скрыты от клиента по умолчанию. Обработчик есть только S-03.
- Светлый glassmorphism: лендинг, кабинет, форма S-03, результат и доступы компании; без задач и командных чатов. Allauth не заменён, Admin не переоформлен.
- Company + owner/member/viewer; несколько учётных записей компании; результаты общие в пределах компании по роли. Владелец добавляет уже зарегистрированные аккаунты, приглашения по email пока не реализованы.
- Синтетический S-03: детерминированный непроверенный черновик претензии об оплате, валидация, DOCX, Celery worker, company-scoped download. Нет подписи, отправки, автоматической неустойки и подтверждённых правовых ссылок.
- ИИ выключен по умолчанию. Отключённый opt-in Zen chat-completions adapter подготовлен, но без нового ключа/модели и реального provider test. GigaChat/YandexGPT не подключены. Ключ из чата не использовался: его нужно отозвать.
- Reliability v2: transactional outbox, контроль state/generation, needs_review для прерванных обработок; без auto-replay ИИ; explicit template-only recovery. Один существующий beat, явная регистрация periodic tasks.

## Доказательства и стоп-факторы
Реально прошли 34 pure unittest (14 движка + 20 reliability), ранее 22 группы Chromium UI checks (не backend), AST новых Python files, XML/DOCX reopen, git apply --check на сохранённых baseline и архивные checksum checks. Пять основных экранов и новый terminal state визуально просмотрены на 1440/390px. В reports есть предыдущие 100-критериальный аудит и 15-факторная оценка: это исторические отчёты v1, reliability changes описаны отдельно.

НЕ выполнены: Docker build/run, полный Django signup/mail/worker/storage flow, 23 selfservice integration tests (10 access +13 outbox), миграционная consistency, реальные гонки PostgreSQL, RLS/tenant isolation, backup restore, чистый offline image transfer, GitHub CI run, VPS/публичный HTTPS/внешний российский S3. uv.lock пока stale относительно инфраструктурных зависимостей: сначала controlled refresh, затем сборка. Garage prod-test file secrets 0444 остаётся отдельным блокером, не исправленным dev-exception. Нельзя считать инфраструктуру/одну услугу принятой или заявлять готовность 90+.

## 1. Перенос в /Users/victorkhudyakov/cpxly
Скачайте Capexly-complete-candidate.zip в Downloads. Команда macOS ниже откажется, если cpxly существует, включая symlink:
```sh
(
  set -eu
  TARGET=/Users/victorkhudyakov/cpxly
  ARCHIVE="$HOME/Downloads/Capexly-complete-candidate.zip"
  test -f "$ARCHIVE"
  if [ -e "$TARGET" ] || [ -L "$TARGET" ]; then
    echo 'СТОП: cpxly уже существует. Не перезаписывайте его; нужен отдельный merge.' >&2
    exit 1
  fi
  ditto -x -k "$ARCHIVE" /Users/victorkhudyakov
)
```
Если папка уже есть, альтернативно распакуйте в новый staging-каталог, не меняя рабочую папку:
```sh
STAGING=$(mktemp -d /Users/victorkhudyakov/cpxly-review.XXXXXX)
ditto -x -k "$HOME/Downloads/Capexly-complete-candidate.zip" "$STAGING"
echo "$STAGING/cpxly"
```
После этого остановитесь для сравнения и согласованного merge. Не переносите старые .env/секреты/dev-volumes в новую конфигурацию автоматически.

## 2. Проверка окружения, без установки программ
```sh
cd /Users/victorkhudyakov/cpxly
uname -m
docker version
docker compose version
docker buildx version
```
Должны быть доступны Docker Engine, Compose v2 и buildx. Если нет — это блокер, установка/настройка Docker требует отдельного разрешения. Python/uv/Node/PG/Redis на macOS не устанавливаются. Цель linux/amd64; на Apple Silicon дальнейшие контейнеры могут работать через эмуляцию, что нужно отметить. Это не заменяет native VPS smoke.

## 3. Устранение lockfile-блокера в контейнере
```sh
docker build --platform linux/amd64 --target tooling -t capexly-tooling .
LOCK_REVIEW_DIR=$(mktemp -d)
cp uv.lock "$LOCK_REVIEW_DIR/uv.lock.before"
docker run --rm --platform linux/amd64 --user "$(id -u):$(id -g)" -v "$PWD:/app" capexly-tooling uv lock
diff -u "$LOCK_REVIEW_DIR/uv.lock.before" uv.lock
```
Просмотрите diff. Exit code 1 у diff означает наличие изменений, не нужно подменять lock вручную или добавлять --upgrade. Проверьте отсутствие неожиданных обновлений стартера. При недоступных версиях/образах остановиться, не менять registry/digest произвольно. После согласования lock diff:
```sh
docker run --rm --platform linux/amd64 --user "$(id -u):$(id -g)" -v "$PWD:/app" capexly-tooling uv lock --check
```
До успешного check дальше не идти. Эти команды в среде агента не выполнялись.

## 4. Свежий isolated synthetic dev
Только для новой папки/окружения, не для перезаписи existing .env:
```sh
cp .env.example .env
```
В .env вручную выставить несекретные значения:
```dotenv
COMPOSE_PROJECT_NAME=capexly-local-v2
SECRETS_DIR=./secrets/dev
APP_IMAGE=capexly-app:local-v2
S3_BUCKET=capexly-synthetic
```
Остальные значения оставить из примера. Не добавлять реальные документы, production keys, Zen token или миграционный пароль в общий env. Затем:
```sh
docker run --rm --platform linux/amd64 --user "$(id -u):$(id -g)" -v "$PWD:/app" capexly-tooling python scripts/dev-secrets.py
dc() { docker compose --env-file .env -f compose.yaml -f compose.dev.yaml -f compose.pilot.dev.yaml "$@"; }
dc config --quiet
dc build
dc up -d --wait db redis garage mailpit
dc run --rm migrate
dc run --rm db-ops
dc run --rm migrate python manage.py makemigrations --check --dry-run
dc run --rm web python manage.py activate_synthetic_pilot --confirm-synthetic-only
dc run --rm web python manage.py bootstrap_celery_tasks
dc up -d web worker beat frontend-dev
dc exec web python manage.py createsuperuser
dc ps
```
Команды миграции идут под отдельной ролью migrate. Web/worker — runtime, не давать ей DDL ради tests. Активация включает только synthetic S-03, а bootstrap добавляет periodic outbox/stale maintenance в один beat. Superuser — только технический оператор, не клиент. При ошибке любой стадии остановиться и сохранить вывод без секретов; не продолжать весь список вслепую.

Открыть:
- http://localhost:8000 — лендинг;
- http://localhost:8000/accounts/signup/ — регистрация клиента;
- http://localhost:8000/cabinet/ — кабинет;
- http://localhost:8000/admin/ — стандартная техническая админка;
- http://localhost:8025 — локальные тестовые письма.

Создать отдельного обычного клиента, пройти onboarding компании, заполнить S-03 только вымышленными сведениями, дождаться worker и скачать DOCX. Это обязательный будущий smoke, а не уже подтверждённый результат. В preview по пути reports/capexly-preview.html есть только кликабельный макет: он не регистрирует аккаунты и скачивает пример TXT, не серверный DOCX.

## 5. Повторный запуск, логи, tests
В новом терминале восстановите функцию dc выше из корня проекта:
```sh
dc up -d
dc ps
dc logs --tail=80 web worker beat garage
dc down
```
Последняя команда останавливает окружение без удаления томов. Не использовать down -v, volume rm и make init. Upstream make init/dev — не поддержанный full-Docker путь.

Pure tests в собранном контейнере:
```sh
dc run --rm web python -m unittest apps.selfservice.tests.test_engine apps.selfservice.tests.test_reliability -v
```
Integration tests требуют ОТДЕЛЬНОЙ CI БД и secrets по docs/testing.md. Не запускать обычный Django test runner с выдачей runtime CREATEDB. Остальные команды восстановления/диагностики — docs/reliability-runbook.md. Простой просмотр заявки:
```sh
dc exec web python manage.py recover_service_request UUID_ЗАЯВКИ
```
Повтор изменяет данные и требует отдельного решения. Он запрещён для use_ai=True, опубликованного файла, активной или готовой заявки. Смешанный запуск worker v1/v2 не поддерживается; перенос существующего проекта требует coordinated rollout и проверенного backup, не только этих fresh-install команд.

## 6. Перенос на VPS — отдельный, пока непроверенный этап
Архив исходников не содержит database/files/volumes и не переносит данные. Не копировать работающий Postgres volume. Нужен проверенный backup set и отдельный restore.

После локальной интеграционной приёмки: свой Git repo/зафиксированный reviewed commit (архив .git не включает), чистое дерево, уникальный release tag; production build linux/amd64 и smoke; затем release-save.sh сохраняет полноценные images и SHA256, release-load.sh сверяет checksum до docker image load. На Linux VPS нужен Docker/Compose, но не Python/Node на хосте. Скрипты release/backup используют Linux sha256sum и возможности свежего Docker (--platform для save/load): не запускать их вслепую на macOS с отсутствующим sha256sum/старым CLI. Их совместимость здесь не проверялась.

Перед реальным VPS отдельно нужны согласование deployment diff, домен/DNS, порты Caddy 80/443, постоянное состояние Caddy, приватный внешний S3, production secrets/SMTP, off-server backup и restore drill. PostgreSQL/Redis/web наружу не публикуются. Dev secrets/data/флаг Garage exception не переносить в prod. ACME staging не равен доверенному production HTTPS. Нельзя отключать TLS-проверку ради теста. Откат image не отменяет migration.
