# Пакет diff v2 для согласования

Garage для dev уже принят. Этот diff НЕ применён к исходному стартеру и
не меняет реальный сервер, роли действующей базы или настройки ОС.

## Порядок просмотра
1. .dockerignore/.gitignore: исключены реальные env, ключи, documents,
   backups/dumps/releases/reports. Явное исключение для infra/postgres/*.sql
   позволяет доставить проверенные init/check SQL, но не пользовательские дампы.
2. Dockerfile: pinned FROM, npm ci, uv --locked, сборка assets/collectstatic,
   production USER 10001:10001, без host Node/Python и секретов в ARG/ENV.
3. Compose: общая основа + взаимоисключающие dev/prod/prod-test overrides.
   Старый docker-compose.yml удаляется только в кандидате; его история в Git
   сохранена. Новые Makefile targets названы capexly-*, upstream команды сохранены.
4. PostgreSQL: bootstrap только в DB; migrator отдельный one-off; web/worker/beat
   получают runtime secret. NOSUPERUSER/NOBYPASSRLS/NOCREATEDB/NOCREATEROLE,
   нет владения таблицами, CREATE/TEMP схемы и членства в migrator. Четыре
   table privileges проверяются КАЖДЫЙ, а не любой один из списка.
5. Django: secure common configuration + строгий prod; отдельные CI/build/test
   modules не используются настоящим deployment. DEBUG forced False до импорта
   базовых settings; explicit hostname/CSRF/secure cookies/proxy/static.
6. Caddy: prod ACME staging/production endpoint выбирается явно; отдельный
   режим external-ca. Test tls internal не запрашивает public сертификаты.
7. Backup/restore/release/CI: явные guards, no destructive volume cleanup,
   checksum до load/restore, чистое окружение и реальные результаты ещё нужны.

## Роли и порты
Dev: localhost 8000, 5173, 3900, 8025. DB/Redis/SMTP не публикуются.
Prod: Caddy 80/443 TCP; нет ports у DB/Redis/web и нет локального S3.
Prod-test: localhost 8443, 3901, 8026; отдельный проект и secrets.
RPC Garage слушает loopback внутри контейнера; admin/web S3 API выключены.
Все обычные остановки сохраняют named volumes.

## Изменения после v1, требующие внимания
- Новый prod-test и локальный test CA: только его public root экспортируется
  в secret file probe, системное хранилище доверия хоста не меняется.
- File-backed secret files генерируются 0444 внутри host directory 0700:
  Compose bind secrets не гарантируют uid/gid remapping. В контейнере каждый
  secret доступен только сервисам, которым он смонтирован. Docker/host admin
  всё равно доверенные. Существующие файлы автоматически не chmod/rotate.
- psycopg prod переключается с [c] на [binary], как dev, с закреплённым libpq
  wheel. Исходный lock уже содержит cp314 manylinux x86_64 wheel 3.3.4, но
  после изменения extras lock нужно штатно обновить и проверить. apt-get
  удалён из app Dockerfile: нет незакреплённых Debian install шагов.
  За security обновления bundled libpq/OpenSSL отвечает обновление этого wheel.
- CI дополнен, существующие tests не меняются ради зелёного результата.
  Prepared test runner не создаёт/мигрирует БД под runtime и не скрывает
  TransactionTestCase: такой новый тест явно заблокирует неподдержанный путь.
- Backup set останавливает web/worker/beat ТОЛЬКО после CONFIRM_PAUSE_WRITES.
  Это окно недоступности; на ошибке writers остаются остановлены. Все внешние
  writers оператор обязан остановить отдельно. Нет online/PITR обещания.
- restore-set автоматизирован только для нового synthetic restore project;
  настоящую production restore операцию нельзя запустить этим скриптом.
- release aliases + image IDs нужны потому, что save/load не гарантирует
  сохранение repo-digest aliases. prod-test archive включает test storage/mail,
  production archive — только actual server services; нельзя их путать.

Garage storage daemon внутри dev/test контейнера пока root с cap_drop ALL и
read-only rootfs; приложение production непривилегированное. Это отдельно
раскрытая конфигурация, не утверждение, что все сервисы непривилегированны.

Все непроведённые проверки перечислены в STATUS.md. Изменения безопасности
не применять без просмотра точного diff и согласования этого пакета.

Release build дополнительно требует clean committed source и уникальный tag.
Image revision должен совпадать с переносимой reviewed конфигурацией.
Одноархитектурный save/load требует Docker API >=1.49 в этом runbook; старый
Docker — блокер, не разрешение автоматического upgrade. Access log Gunicorn
не содержит path/query: меньше диагностики маршрута, зато не пишет URL tokens.
