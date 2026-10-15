# Запуск и диагностика очереди — кандидат v2

Все команды ниже — на будущее, после ревью и согласования. Здесь они НЕ выполнялись. Требуется предыдущий selfservice-пакет и уже проверенный full-Docker dev. Если нет Docker/Compose, остановиться; не заменять services-only и не устанавливать host dependencies без подтверждения.

## Проверка diff
```sh
git status --short
git apply --check /путь/к/reliability.patch
# Прочитать diff и docs/reliability-review.md, затем только после согласования:
git apply /путь/к/reliability.patch
git diff --check
```
Если baseline другой — остановиться, не использовать force/reset/слепую перезапись source.

## Перед миграцией
Сначала устранить прежний uv.lock blocker и выполнить прежние docs/local-start.md и docs/selfservice-start.md в synthetic dev. Не копировать заново уже существующие .env или секреты. Не запускать новые миграции в неизвестной production БД.

Из-за generation protocol не поддерживается смешивание старых и новых web/worker. Согласовать окно обновления; дождаться завершения активных задач старого worker, затем остановить web/worker/beat без удаления томов. Если активный ИИ-запрос не завершается — сначала разбор, не принудительный kill ради этого руководства. Проверенный backup перед изменением схемы обязателен; его restore ранее здесь не проверялся.

## Новый согласованный synthetic dev
```sh
dc() { docker compose --env-file .env -f compose.yaml -f compose.dev.yaml -f compose.pilot.dev.yaml "$@"; }
# Только после безопасной остановки старой версии и подготовки зависимостей:
dc config --quiet
dc build
dc up -d --wait db redis garage mailpit
dc run --rm migrate
dc run --rm db-ops
dc run --rm migrate python manage.py makemigrations --check --dry-run
# Штатная команда стартера. Новая регистрация явная, без --remove-stale.
dc run --rm web python manage.py bootstrap_celery_tasks
dc up -d web worker beat frontend-dev
```
Остаётся один beat. Bootstrap регистрирует 30-секундный outbox и 60-секундную проверку stale. Время обработки клиента не обещается равным этим интервалам. Миграция не запускает задачи и не вызывает внешние API.

## Неизменяющий просмотр конкретной заявки
```sh
dc exec web python manage.py recover_service_request UUID_ЗАЯВКИ
```
Печатаются state/attempts/ai/file, не факты, тексты, email или секреты. Без флагов состояние не меняется. Состояния и outbox также видны техническому staff в стандартном Django Admin.

## Ручное восстановление — только после отдельного решения оператора
```sh
# Только non-AI synthetic failed/needs_review, без готового файла и с attempts<3:
dc exec web python manage.py recover_service_request UUID_ЗАЯВКИ --apply --confirm-template-only
```
Запрос с ИИ будет отвергнут, независимо от этих флагов. Активный processing, queued и ready тоже будут отвергнуты. Команда не удаляет записи/файлы, не меняет роли/схему и не пересоздаёт заявку. Она возобновляет тот же synthetic template request с новой generation. Не повторять команду вслепую и не менять use_ai/state через SQL ради обхода запрета.

Если beat недоступен, технические maintenance-функции можно запустить явно в контейнере после просмотра их назначения:
```sh
# Изменяет queued delivery metadata и публикует сообщения для queued:
dc exec web python manage.py shell -c 'from apps.selfservice.tasks import dispatch_pending; dispatch_pending()'
# Помечает processing старше 15 мин как прерванные, без повтора ИИ:
dc exec web python manage.py shell -c 'from apps.selfservice.tasks import mark_stale_processing; mark_stale_processing()'
```
Это не замена постоянному beat и не автоматическая безопасная команда для production. При полностью недоступной БД ничего из этого не восстановит заявку: требуется диагностика БД.

## Тесты
Чистые правила в контейнере, без PostgreSQL/Redis/S3:
```sh
dc run --rm web python -m unittest apps.selfservice.tests.test_engine apps.selfservice.tests.test_reliability -v
```
DB integration — только отдельный prepared CI по docs/testing.md, schema создаёт migrator, tests идут под capexly_runtime:
```sh
CAPEXLY_ENV_FILE=.env.ci COMPOSE_PROJECT_NAME=capexly-ci SECRETS_DIR=./secrets/ci ./scripts/runtime-tests.sh apps.selfservice.tests.test_outbox apps.selfservice.tests.test_access
```
Не выдавать runtime CREATEDB или владение таблицами для tests. Fault injection через mocks в подготовленных tests не подтверждает реальную связь Redis/Garage. Отдельно после этого провести реальные остановку/возврат Redis, потерю сообщения, worker kill после provider call, поздний save, revoke membership и S3 timeout. Действительно конкурентный PG multi-connection harness ещё не добавлен: текущий prepared runner запрещает TransactionTestCase, не следует ослаблять этот guard без отдельного дизайна.

## Откат
Откат image не отменяет schema migration. После её применения не запускать старый worker вместе с новым. Выбранный релиз должен поддерживать этот протокол; безопаснее остановить обработку до согласованного исправления, чем менять state вручную. Обратная миграция удалит новую таблицу/поля — не выполнять без отдельного подтверждения и проверенного backup. Команд down -v, volume rm, DROP в этом руководстве нет.
