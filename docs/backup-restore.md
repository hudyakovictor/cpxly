# Backup/restore и откат — непроверенный кандидат

PostgreSQL17: pg_dump -Fc и pg_restore из того же закреплённого Postgres image.
Не копировать работающий PG volume. В backup set входят schema/data dump,
current private objects, metadata и SHA256 manifest. Object history/versioning,
delete markers, provider bucket policies/ACL и PITR этим способом НЕ сохраняются.
Future provider/versioning needs отдельный план.

## Согласованный backup
BACKUP_ROOT должен существовать на согласованном отдельном storage, не внутри
project. Production backup копия должна быть off-server, encrypted и restricted;
скрипт не создаёт cloud account и не выполняет невыбранное шифрование/transport.
Подтверждения являются аттестацией оператора, а не доказательством размещения.
```sh
export BACKUP_ROOT=/approved-separate-storage
export BACKUP_SET_ID=synthetic-check-001
export BACKUP_SEPARATE_STORAGE_CONFIRMED=yes
# Только для prod дополнительно OFFSERVER_BACKUP_TARGET_CONFIRMED=yes.
CONFIRM_PAUSE_WRITES=yes ./scripts/backup-set.sh
```
Это подтверждает maintenance outage: web/worker/beat будут остановлены.
Остановить также ВСЕ внешние writers. Dump и objects снимаются в одном окне.
На ошибке writers остаются остановлены, partial output не считается backup.
На успехе проверить checksum и off-server transport, затем ЯВНО:
`./scripts/compose.sh up -d web worker beat`.
Никогда не включать backup/client data в Git или release image archive.

## Восстановление в новый synthetic project
Генерировать secrets с `--environment restore-test`. Сначала нужен новый
project, не исходные volumes; тот же release image и совместимый PostgreSQL.
Не запускать migrate перед schema restore. Сначала roles/empty bucket bootstrap.
```sh
export CAPEXLY_MODE=prod-test
export CAPEXLY_ENV_FILE=.env.restore-test
export COMPOSE_PROJECT_NAME=capexly-restore-review
export SECRETS_DIR=./secrets/restore-test
export APP_IMAGE=capexly-app:<source-release-id>
RESTORE_INTO_EMPTY_ENVIRONMENT=yes ./scripts/restore-set.sh /approved-separate-storage/synthetic-check-001
```
Подготовить .env.restore-test и локальные service images заранее. Если source test работает, его нужно остановить перед target startup, чтобы
освободить localhost test ports; его тома не удаляются. Пустая DB проверяется SQL; существующие objects вызывают отказ.
Target bucket обязан быть пустым. pg_restore --exit-on-error --single-transaction,
никаких --clean/DROP/down-v/volume-rm. Objects checksum проверяется до записи;
после restore выполняется SDK download/hash и существующая user/file связь.
Весь вывод сохранить как реальные recovery evidence; сейчас restore НЕ выполнен.

Test secrets НЕ восстанавливаются из DB/object backup. Fixture verify не меняет
исходный user password; новый restore-test smoke password не позволит войти
под старым hash. Для дополнительного login теста можно отдельно согласовать
перенос ТОЛЬКО synthetic smoke password; production secrets так не переносить.

Production restore требует отдельного подтверждённого runbook под фактическое
storage и сервер: restore-set специально запрещает его автоматический запуск.

## Откат
Сохранять предыдущие images/archives и DB/object recovery set. Откат образа НЕ
отменяет DB migration. Перед откатом проверить совместимость schema. Restore
DB уничтожает более поздние записи: согласовать data-loss window и простой.
Разрушительные команды автоматически не предоставляются и не выполняются.
