# Frontend: видео → MIDI

React + Vite. Загрузил видео → увидел прогресс → скачал `.mid`.

## Запуск с заглушкой (backend не нужен)

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

Нужен Node.js 18 или новее.

## Запуск с настоящим backend

1. Запусти backend (папка `guitar-fingering-ai-backend`, нужны Python 3.11 и ffmpeg в PATH):
   ```bash
   uv run python -m src.main      # слушает http://127.0.0.1:8000
   ```
2. В папке `frontend` скопируй `.env.example` в `.env` и поставь:
   ```
   VITE_USE_MOCK=false
   ```
3. Запусти (или перезапусти) `npm run dev`. Страница открывается как обычно на http://localhost:5173,
   запросы к `/upload`, `/status`, `/result` Vite пересылает на backend сам (прокси в `vite.config.js`).

Весь код общения с backend — в `src/api.js`: `uploadVideo`, `getStatus`, `downloadResult`.

## Проверка

- любой `.mp4` / `.mov` → загрузка → этапы обработки → «Результат готов!» → скачивается `.mid`;
- заглушка: файл с `fail` в имени (например `fail.mp4`) → ошибка обработки;
- другой формат или файл больше 500 МБ → баннер ошибки на странице загрузки.
