# Локальная разработка полностью в Docker — кандидат

Сначала STATUS.md и review-packet.md. Требуются Docker/Compose v2/buildx;
Make необязателен. Python, uv, Node, PostgreSQL и Redis на хост не устанавливаем.
В текущей среде эти команды НЕ выполнялись. Установка Docker — отдельно.
Цель linux/amd64; на ARM сборка и запуск могут идти через эмуляцию: отметить
это в отчёте. Успешной сборки недостаточно, smoke обязателен.

## После согласования diff
```sh
cp .env.example .env
# В .env: APP_IMAGE=capexly-app:dev; dev project и secrets/dev, без prod ключей.
docker build --target tooling -t capexly-tooling .
docker run --rm --user "$(id -u):$(id -g)" -v "$PWD:/app" capexly-tooling uv lock
# Просмотреть uv.lock diff; проверить сохранение версий стартера, не --upgrade.
docker run --rm -v "$PWD:/app" capexly-tooling uv lock --check
docker run --rm --user "$(id -u):$(id -g)" -v "$PWD:/app" capexly-tooling python scripts/dev-secrets.py
./scripts/compose.sh config --quiet
./scripts/compose.sh build
./scripts/compose.sh up -d --wait db redis garage mailpit
./scripts/compose.sh run --rm migrate
./scripts/compose.sh run --rm db-ops
./scripts/compose.sh up -d
./scripts/compose.sh exec web python manage.py createsuperuser
./scripts/compose.sh exec web python manage.py bootstrap_celery_tasks
./scripts/compose.sh run --rm migrate python scripts/storage-smoke.py
```
Не используйте upstream make init: host tools и автоматическое makemigrations.
Новые capexly-* команды добавлены нами в custom.mk, исходные targets сохранены.

Web localhost:8000, Vite localhost:5173, Garage localhost:3900, Mailpit
localhost:8025. Внутренний S3 SDK endpoint garage:3900; подписанные ссылки
генерируются для browser localhost, НЕ переписываются после подписи.

Последующие запуски: `make capexly-up`; остановка: `make capexly-down`.
Тома остаются. При изменении dependencies нужен reviewed rebuild и controlled
refresh dev_venv/dev_node_modules; не удалять data volumes. Команда destructive
cleanup не предоставляется. Безопасное обновление dependency volumes пока
требует отдельной проверки, чтобы не запускаться со старым venv.

Только синтетические данные/письма; AI stub не имеет провайдера, внешние вызовы
не включаются флагом: adapter с включённым флагом ошибается, а не вызывает сеть.
Не добавлять production creds/договоры в исходники или bind mounts.

Секреты создаются только для dev, не печатаются. Existing files не перезаписываются.
Если уже создан secret v1 с mode 0600 и отличным от UID10001 владельцем,
нужно отдельно согласовать его доступ; генератор не исправляет это молча.
Формат Garage key GK+hex проверяется до server startup. Не менять key/RPC
на заполненном Garage без отдельного плана ротации.

Тесты нельзя запускать обычным Django test runner под runtime с CREATEDB.
Нужно отдельное prepared CI окружение: см. testing.md. Не расширять runtime
привилегии ради тестов или makemigrations.
