# Статус кандидата v2 — НЕ ПРИНЯТ / НЕ ГОТОВ К DEPLOYMENT

Исходный commit: e9d11b0a294191af87fec6f84acb4d96454957be.
Исходная копия стартера не изменена. Бизнес-логики и tenant isolation нет.
Garage принят пользователем только для dev; production использует внешний S3.

## Реально выполнено
- Аудит бесплатного стартера: README, Makefile, настройки, lockfiles, CI.
- Проверены официальные manifests/digest/amd64 у базовых сервисов.
- Все config/layer blobs Garage amd64 скачаны анонимно и проверены SHA-256.
- Проверки синтаксиса Python AST, YAML и sh -n; git diff --check.
- Дополнительные проверки исходной конфигурации описаны в static-checks.txt.
- Проверка синтетического генератора секретов — только стандартным Python,
  без Docker и без печати значений; это не проверка Compose secret mounts.

## Подготовлено, но НЕ выполнялось
- Полный dev, отдельный production-test с собственными томами/секретами.
- Gunicorn/WhiteNoise/Caddy, тестовый локальный CA и supplied external CA.
- Runtime-role CI, отрицательные тесты DDL/смены роли/изменения RLS.
- Реальные smoke-команды: HTTPS/CSRF/login/static, local SMTP, private S3,
  отдельный worker и сохранность связи user -> file после restart/restore.
- DB+object backup set, восстановление в пустое synthetic окружение.
- Перенос save/load с image ID, release aliases и --pull never.

## Блокеры
1. В текущей агентской среде НЕТ Docker executable/daemon/buildx/Compose.
2. uv.lock пока исходный; pyproject изменён. uv lock refresh/review/check
   обязателен. --locked build и CI должны отказаться работать с устаревшим lock.
3. Django/pytest/lint/type-check/frontend build/container smoke НЕ запускались.
4. CI workflow написан, но не отправлялся в GitHub и не запускался.
5. Полная безопасность image layers и совместимость Compose не подтверждены
   статическим разбором YAML или осмотром финальной файловой системы.
6. Шифрование, off-server transport, retention и alert destination требуют
   согласованного operational окружения; никаких аккаунтов не создано.
7. VPS/домен/облачный S3 не предоставлены: deployment, публичный ACME staging,
   доверенный production HTTPS и облачная S3-совместимость НЕ ПРОВЕРЕНЫ.

Нельзя загружать реальные клиентские документы. Организации, продуктовые
права и RLS — следующий этап. Не заявлять критерии приёмки выполненными.
