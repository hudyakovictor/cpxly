# Проверки: команды подготовлены, результаты ещё не получены

## CI
Новый .github/workflows/capexly-infrastructure.yml собирает tooling, проверяет
lock, строит prod amd64 image, проверяет USER, готовит disposable PostgreSQL,
мигрирует отдельной ролью, запускает tests под runtime и стартует Gunicorn
из release image с CI-only настройками. Это не проверка внешнего production.
Существующий CI сохранён; PostgreSQL/Redis images закреплены; npm install
заменён npm ci. Upstream privileged tests не доказывают runtime безопасность.
CI никуда не отправлялся, credentials GitHub не использовались.

PreparedDatabaseRunner сохраняет TestCase transaction isolation, но не делает
CREATE/DROP/migrate/flush под runtime. Parallel DB и TransactionTestCase пока
не поддерживаются: явно fail, а не skip. Новые access tests требуют PostgreSQL
SQLSTATE 42501 для запрета CREATE/ALTER/RLS/policy/SET ROLE. Tenant isolation
не проверяется этим тестом и не реализована.

Ручной runtime test при УЖЕ prepared isolated DB:
```sh
export COMPOSE_PROJECT_NAME=capexly-ci-review
export SECRETS_DIR=./secrets/ci
export APP_IMAGE=capexly-tests:ci
export CAPEXLY_ENV_FILE=.env.ci
./scripts/runtime-tests.sh
```
Сначала отдельно подготовить секреты, DB и migrate, как в CI. Не менять роли
или тесты ради зелёного результата.

## Production-like test без dev данных
APP_IMAGE — уже построенный/проверяемый production image, НЕ dev image.
Сборку выполнять только после review, lock refresh и commit, через
`APP_IMAGE=capexly-app:<release-id> ./scripts/release-build.sh`.
```sh
docker run --rm --user "$(id -u):$(id -g)" -v "$PWD:/app" capexly-tooling python scripts/dev-secrets.py --environment prod-test
cp .env.example .env.prod-test
export CAPEXLY_MODE=prod-test
export CAPEXLY_ENV_FILE=.env.prod-test
export COMPOSE_PROJECT_NAME=capexly-test-review
export SECRETS_DIR=./secrets/prod-test
export APP_IMAGE=capexly-app:<release-id>
./scripts/compose.sh config --quiet
# Подготовить test storage image отдельно; app НЕ пересобирается здесь.
./scripts/compose.sh build garage
./scripts/compose.sh pull db redis caddy mailpit
CONFIRM_RESTART_SYNTHETIC=yes ./scripts/prod-test-smoke.sh
```
Скрипт выполняет migrate/grants, старт web/worker/beat/Caddy, экспорт только
public local CA, private upload/presigned GET/anonymous403, существующую
авторизацию через HTTPS+CSRF, built static и письмо в Mailpit. Отдельный worker
возвращает token и current_user=capexly_runtime. Exactly one beat.
После подтверждённого restart сравнивается DB user -> avatar file и hash.
Ошибки не скрываются. Object smoke сохраняет только новые synthetic objects.

Probe доверяет именно экспортированному test CA через свой SSLContext,
не verify=False и не host system CA. Test domain resolves через Docker alias;
хосту DNS/trust менять не нужно. Local browser без отдельного trust setup
будет показывать недоверенный сертификат — это ожидаемо.

Это не staging ACME issuance, не trusted public production HTTPS, не cloud S3.
Для этих проверок нужны предоставленные реальные domain/VPS/provider.

## Clean transfer
Отдельный Compose project НЕ является пустым Docker image cache. Для настоящего
save/load теста нужна другая разрешённая машина/daemon без исходных images и
volumes. Не стирать текущий daemon. Загрузить архив, проверить IDs/architecture,
запускать с release override, --no-build --pull never. Для local synthetic
transfer можно упаковать prod-test services, но такой архив не серверный релиз.
Ни Docker, ни создание новой VM/daemon здесь не выполнены.
