# Каталог услуг: только административные заглушки

## Что меняется
Добавляется app service_catalog, одна глобальная таблица метаданных, две явные
миграции (schema + F1 snapshot) и регистрация в штатном Django Admin. Все S-01–S-57
сохранены, но ни одна запись пока не активна и не видна клиенту. Нет клиентских
routes, форм заказов, командных задач/чатов, AI вызовов и новых прав пользователей.
Django auth/Admin тема и существующие роли PostgreSQL не переписываются.

Пакет — кандидат для review, НЕ запись в вашу работающую БД. Для применения
нужна explicit migrate под migrator. Автоматического makemigrations на startup нет.
Новых dependencies нет. Последующие версии seed snapshot не заменяют v1.

## Что видно в /admin/
Каталог услуг -> услуги и функции платформы. Поля: стабильный ID, название,
тип записи, приоритет исходного F1, фактический этап, обработчик/возможность заказа,
исходные описания/блокеры/оговорки и собственные заметки администратора.
Все записи первоначально «Заглушка», скрыты, заявки выключены.
MVP в исходнике НЕ означает «реализовано». Блокер «нет» из архива не является
результатом проверки интеграции. Классификационные противоречия S-09/S-10/S-28
помечены отдельно, а не исправлены молча. S-01 — пакет; S-36–S-46 — инфраструктура
продукта; S-53–S-57 — GTM, не отдельные готовые клиентские услуги.

## Команды в существующем dev проекте
Сначала review/apply patch, сохранить текущие secrets/project/volumes.
```sh
export CAPEXLY_MODE=dev
./scripts/compose.sh run --pull never --rm migrate
./scripts/compose.sh run --pull never --rm db-ops
./scripts/compose.sh restart web
```
Открыть http://localhost:8000/admin/ под уже существующим superuser.
Если администратора ещё нет: `./scripts/compose.sh exec web python manage.py createsuperuser`.
Обычная регистрация клиента не даёт is_staff/superuser или права каталога.
Отсутствующие seed записи можно добавить отдельно без изменения уже существующих:
`./scripts/compose.sh run --pull never --rm web python manage.py seed_service_catalog`.
Команда не включает заглушки, не обновляет заметки/названия и не удаляет записи.

В dev исходники bind-mounted, dependency changes нет — обычно build не нужен.
В production нужен НОВЫЙ reviewed release image из clean committed source,
миграция отдельной ролью и smoke; копирование файлов в running container запрещено.
Не откатывать schema к zero: это удалит таблицу каталога. Такой rollback не выполнялся.

## Подключение следующей услуги
1. Уточнить scope, входы, выход, ограничения и applicability; не копировать
   исследовательские юридические формулировки как готовые правила.
2. Реализовать серверный handler в trusted code и явно зарегистрировать по ID.
   Не исполнять Python/module paths, prompts или команды из полей админки.
3. Использовать общий self-service путь: ввод -> обработка -> результат.
   Нужны company/user access checks, private files, worker context и audit.
   Никаких обязательных чатов, менеджеров или постановки задач между людьми.
4. Для AI — provider adapter, секрет ТОЛЬКО на сервере, synthetic test first,
   timeouts/лимиты/повторы/стоимость и проверка структурированного результата.
   Сейчас handlers/AI не подключены. Ключи не хранятся в каталоге или seed.
5. Тесты access isolation, повреждённых входов, ошибок API, idempotency, экспорта
   и регрессии существующей услуги. У роли runtime нет schema privileges.
6. Только после проверок отдельно разрешить видимость/приём заявок. Placeholder
   нельзя включить через admin; UI статус сам по себе не доказывает готовность.

## Проверка
Django tests: apps.service_catalog.tests в УЖЕ prepared isolated runtime-role CI DB
(не запускать обычный test runner с CREATE DATABASE под runtime). Новые миграции
обязательно должны войти в подготовку этой DB. `makemigrations --check --dry-run`
после review проверяет синхронность model/migration, а не генерирует новые файлы.
Docker/Django test/migration execution в агентской среде НЕ выполнены: их нет.
AST/JSON/source checks выполнены отдельно и не заменяют эти проверки.
