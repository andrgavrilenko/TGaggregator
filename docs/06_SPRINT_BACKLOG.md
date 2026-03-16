# 06 Sprint Backlog

## P0 (обязательно)

- [ ] Scaffold проекта и dependency management.
- [ ] DB schema + migrations.
- [ ] Telegram login/session manager.
- [ ] Channels bootstrap + toggle state.
- [ ] Incremental ingestion + dedup.
- [ ] Feed API.
- [ ] Streamlit feed UI.
- [ ] Status endpoint/panel.
- [ ] Service autostart.

## P1 (после MVP)

- [ ] Read/unread state.
- [ ] Дедуп похожих кросспостов.
- [ ] Digest/alerts.
- [ ] Расширенная аналитика по каналам.

## Зависимости между задачами

1. DB schema -> ingestion/API.
2. Ingestion -> feed API.
3. Feed API -> UI.
4. QA/ops после стабилизации P0.

## Definition of Done (спринт)

- Все P0 закрыты.
- Есть runbook запуска.
- Есть статусная панель и журнал ошибок.
- Базовые smoke-тесты проходят.
