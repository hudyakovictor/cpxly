# Применение и проверка кандидата

Это инструкции на будущее после согласования diff. В текущей среде они не выполнялись. Не устанавливать Python/Node/uv на хост; все проектные команды выполняются в контейнерах. Нужны заранее согласованные Docker/Compose/buildx.

## Безопасное применение
Архив — feature-only delta к ранее подготовленному кандидату инфраструктуры+каталога. Не копируйте папку source поверх вашего проекта. Если предыдущий каталог не применён, сначала согласуйте его отдельный пакет. Base commit бесплатного стартера указан в review. baseline.json фиксирует SHA256 пяти изменяемых ранее существовавших файлов; весь пакет не является Git commit вашего проекта.

```sh
git status --short
# Проверить в рабочей ветке; если есть незакоммиченные изменения — сохранить, не reset.
git apply --check /путь/к/feature.patch
git diff --stat
# Прочитать feature.patch и docs/selfservice-review.md.
# Только после согласования:
git apply /путь/к/feature.patch
git diff --check
```

Если --check выдаёт ошибку — остановиться и сопоставить текущие файлы; не применять --reject/--force и не перезаписывать настройки. Сам patch содержит новые модели и dev-overlay, поэтому review обязателен даже если --check зелёный.

## Новый синтетический dev после устранения lockfile-блокера
Сначала выполнить прежний docs/local-start.md: tooling build → controlled uv lock → просмотр diff → uv lock --check → только dev secrets → build. Не использовать upstream make init (host dependencies/автоматическое makemigrations).
Если окружение уже работает, не копировать .env и не пересоздавать секреты/тома.

```sh
# Запускать из корня проекта; .env — только синтетический dev.
export CAPEXLY_MODE=dev
# Эта функция не подменяет prod-конфигурацию.
dc() { docker compose --env-file .env -f compose.yaml -f compose.dev.yaml -f compose.pilot.dev.yaml "$@"; }
dc config --quiet
dc build
dc up -d --wait db redis garage mailpit
# Схема — только migrator; не web/worker:
dc run --rm migrate
# Ограниченные права runtime, проверка после миграций:
dc run --rm db-ops
# Сравнить модели и миграции; ничего не генерируется:
dc run --rm migrate python manage.py makemigrations --check --dry-run
# Явная активация ровно S-03 в синтетическом контуре:
dc run --rm web python manage.py activate_synthetic_pilot --confirm-synthetic-only
dc up -d web worker beat frontend-dev
dc exec web python manage.py createsuperuser
```

Сайт http://localhost:8000, кабинет /cabinet/, стандартная админка /admin/, почта http://localhost:8025. Первый зарегистрированный клиент создаёт компанию, owner добавляет уже зарегистрированные аккаунты. Вход/регистрация/письма нужно проверить реально; HTML-превью этого не делает. Superuser — только техническому оператору, не клиенту.

Повторный запуск: `dc up -d`; обычная остановка: `dc down` (БЕЗ -v, тома сохраняются). Сначала восстановить функцию dc в новом терминале. Не использовать старые services-only команды как замену этому режиму.

## Тесты

Чистые tests движка (в уже собранном контейнере; внешней сети не требуют):
```sh
dc run --rm web python -m unittest apps.selfservice.tests.test_engine -v
```
Интеграционные tests — отдельное prepared CI окружение с синтетическими данными, миграциями под migrator и тестами под runtime. Не выдавать runtime CREATEDB/DDL ради запуска tests. После подготовки по docs/testing.md:
```sh
CAPEXLY_ENV_FILE=.env.ci COMPOSE_PROJECT_NAME=capexly-ci SECRETS_DIR=./secrets/ci ./scripts/runtime-tests.sh apps.selfservice apps.service_catalog
```
CI базового инфраструктурного кандидата обнаруживает новые tests автоматически, но ещё не запускался. Новая миграция и layout требуют реального smoke, включая allauth signup/login/reset, email, отказ viewer, чужой request UUID, download, брокер failure, revoke, repeated POST и перезапуск.

## ИИ
Не включается этим overlay. Сначала отозвать опубликованный ключ. Затем отдельным согласованным dev overlay монтировать новый secret-файл ТОЛЬКО worker, выбрать совместимую chat-completions модель и включить CAPEXLY_EXTERNAL_AI_ENABLED/PROVIDER=zen/MODEL/KEY_FILE для согласованных процессов. Встроенного рабочего такого secret-overlay здесь нет; внешний запрос не тестировался. UI optional flag виден в Django form только после явного включения; это не разрешение передавать реальные данные. Сначала уточнить цену/лимит/формат модели. По умолчанию используйте шаблонный черновик.

## Backup и откат
Использовать прежние docs/backup-restore.md и scripts/backup-set.sh/restore-set.sh; этот feature patch их не меняет. В backup теперь должны попасть Company/Membership/ServiceRequest/RequestEvent и selfservice/{company}/{request} файлы. Restore проверять по связанному request и скачиваемому DOCX, не только row count. Реальная проверка здесь не выполнена.

Откат кода не отменяет миграции. Старые таблицы не удалять ради отката. Перед миграцией нужен проверенный backup; обратные миграции и удаление файлов требуют отдельного подтверждения. При неизвестном состоянии БД остановиться, не DROP и не down -v.
