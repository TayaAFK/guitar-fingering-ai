// Всё общение с backend — в этом файле: три функции.
//   uploadVideo(file, onProgress) -> { taskId }
//   getStatus(taskId)             -> { status, stage, tempo?, instrument?, message? }
//   downloadResult(taskId, name)  -> скачивает .mid
//
// Режим выбирается переменными окружения (см. .env.example):
//   VITE_USE_MOCK=true|false   (по умолчанию true — заглушка)
//   VITE_API_URL=http://...    (нужен при VITE_USE_MOCK=false)

export const USE_MOCK = import.meta.env.VITE_USE_MOCK !== 'false'
const API_URL = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')

/* ───────────── Публичные функции ───────────── */

export function uploadVideo(file, onProgress) {
  return USE_MOCK ? mockUpload(file, onProgress) : realUpload(file, onProgress)
}

export function getStatus(taskId) {
  return USE_MOCK ? mockStatus(taskId) : realStatus(taskId)
}

export function downloadResult(taskId, fileName = 'result.mid') {
  return USE_MOCK ? mockDownload(fileName) : realDownload(taskId, fileName)
}

/* ───────────── Нормализованный ответ статуса ─────────────
   status: 'processing' | 'done' | 'error'
   stage:  1 — определение инструмента, 2 — анализ аппликатуры, 3 — формирование MIDI
   tempo, instrument — необязательные, показываются на экране результата
   message — текст ошибки от backend
*/

/* ───────────── Настоящий API (backend Славы, FastAPI) ─────────────
   POST /upload       multipart, поле "file" -> 202 { task_id, status, ... }
   GET  /status/{id}  -> { status: queued|processing|completed|failed,
                           stage: extracting_audio|transcribing|null,
                           error: { code, message } | null, ... }
   GET  /result/{id}  -> файл .mid. 409 — ещё не готов, 404 — не найдена или
                         истекла (результат хранится около часа), 422/500 — обработка не удалась
*/

// Статус backend -> шаг на экране (индекс в STEPS из App.jsx):
// 0 «Загрузка видео» (идёт в браузере), 1 «Ожидание в очереди» (queued),
// 2 «Извлечение звука» (extracting_audio), 3 «Формирование MIDI» (transcribing).
const STAGE_TO_STEP = { queued: 1, processing: 2, extracting_audio: 2, transcribing: 3 }

// Коды ошибок обработки (ErrorCode в backend) -> понятный текст.
const ERROR_TEXTS = {
  invalid_media: 'Файл повреждён или это не видео. Попробуйте другой файл.',
  no_audio_track: 'В видео нет звуковой дорожки. Загрузите ролик со звуком.',
  timeout: 'Обработка заняла слишком много времени. Попробуйте более короткое видео.',
  audio_extraction_failed: 'Не удалось достать звук из видео. Попробуйте другой файл.',
  transcription_failed: 'Не удалось превратить звук в ноты. Попробуйте другой ролик.',
  internal_error: 'Ошибка на сервере. Попробуйте ещё раз позже.',
}

// Backend принимает только video/mp4 и video/quicktime, а браузер (особенно на Windows)
// иногда не заполняет тип .mov-файла — тогда подставляем его по расширению.
const MIME_BY_EXT = { mp4: 'video/mp4', mov: 'video/quicktime' }
function withMime(file) {
  if (file.type) return file
  const ext = file.name.split('.').pop().toLowerCase()
  return MIME_BY_EXT[ext] ? new File([file], file.name, { type: MIME_BY_EXT[ext] }) : file
}

function uploadErrorText(status, responseText) {
  let detail = ''
  try {
    const d = JSON.parse(responseText).detail
    detail = typeof d === 'string' ? d : (d?.message ?? '')
  } catch { /* тело не JSON — не страшно */ }

  if (status === 400) {
    if (/duration/i.test(detail)) {
      const sec = Number((detail.match(/(\d+) seconds/) || [])[1])
      return sec
        ? `Видео слишком длинное. Максимальная длительность — ${Math.max(1, Math.round(sec / 60))} мин.`
        : 'Видео слишком длинное.'
    }
    if (/empty/i.test(detail)) return 'Файл пустой. Выберите другое видео.'
    return 'Сервер не принял файл. Проверьте, что это видео в формате MP4 или MOV.'
  }
  if (status === 413) return 'Файл слишком большой для сервера.'
  if (status === 415) return 'Этот формат не поддерживается. Загрузите файл в формате MP4 или MOV.'
  if (status === 503) return 'Сервер сейчас занят. Попробуйте ещё раз через минуту.'
  return `Сервер вернул ошибку (код ${status}). Попробуйте позже.`
}

function realUpload(file, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', `${API_URL}/upload`)
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onProgress?.(Math.round((e.loaded / e.total) * 100))
    }
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const taskId = JSON.parse(xhr.responseText).task_id
          if (!taskId) throw new Error('no task id')
          onProgress?.(100)
          resolve({ taskId: String(taskId) })
        } catch {
          reject(new Error('Сервер вернул неожиданный ответ. Попробуйте ещё раз.'))
        }
      } else {
        reject(new Error(uploadErrorText(xhr.status, xhr.responseText)))
      }
    }
    xhr.onerror = () => reject(new Error('Нет соединения с сервером. Проверьте, что backend запущен, и попробуйте снова.'))
    const body = new FormData()
    body.append('file', withMime(file), file.name)
    xhr.send(body)
  })
}

async function realStatus(taskId) {
  const res = await fetch(`${API_URL}/status/${encodeURIComponent(taskId)}`)
  if (res.status === 404) throw new Error('Задача не найдена или уже удалена с сервера. Загрузите видео заново.')
  if (!res.ok) throw new Error(`Не удалось получить статус (код ${res.status}).`)
  return normalizeStatus(await res.json())
}

async function realDownload(taskId, fileName) {
  const res = await fetch(`${API_URL}/result/${encodeURIComponent(taskId)}`)
  if (res.status === 404) throw new Error('Результат больше недоступен: на сервере файлы хранятся около часа. Загрузите видео заново.')
  if (res.status === 409) throw new Error('Результат ещё не готов. Подождите немного и нажмите ещё раз.')
  if (!res.ok) throw new Error(`Не удалось скачать файл (код ${res.status}).`)
  saveBlob(await res.blob(), fileName)
}

// Единственное место, где ответ backend приводится к формату фронтенда.
// Темп и инструмент backend пока не возвращает — карточки на экране результата тогда скрыты.
function normalizeStatus(raw) {
  switch (raw.status) {
    case 'completed':
      return { status: 'done', tempo: raw.tempo, instrument: raw.instrument }
    case 'failed':
      return { status: 'error', message: ERROR_TEXTS[raw.error?.code] || 'Не удалось обработать видео. Попробуйте другой файл.' }
    default:
      return { status: 'processing', stage: STAGE_TO_STEP[raw.stage ?? raw.status] ?? 1 }
  }
}

/* ───────────── Заглушка ─────────────
   Загрузка ~1,5 с, затем три этапа по 2,5 с и «готово».
   Чтобы проверить экран ошибки обработки, назовите файл с "fail" (например fail.mp4).
*/

const MOCK_STAGE_MS = 2500
const mockTasks = new Map()
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

async function mockUpload(file, onProgress) {
  for (let p = 0; p <= 100; p += 10) {
    onProgress?.(p)
    await sleep(150)
  }
  const taskId = `mock-${Math.random().toString(36).slice(2, 8)}`
  mockTasks.set(taskId, { startedAt: Date.now(), fail: /fail/i.test(file.name) })
  return { taskId }
}

async function mockStatus(taskId) {
  await sleep(150)
  const task = mockTasks.get(taskId)
  if (!task) throw new Error('Задача не найдена.')
  const stage = 1 + Math.floor((Date.now() - task.startedAt) / MOCK_STAGE_MS)
  if (task.fail && stage >= 2) {
    return { status: 'error', message: 'Не удалось найти гитару на видео. Попробуйте другой ролик.' }
  }
  if (stage > 3) return { status: 'done', tempo: 96, instrument: 'гитара' }
  return { status: 'processing', stage }
}

async function mockDownload(fileName) {
  await sleep(200)
  saveBlob(new Blob([buildDemoMidi()], { type: 'audio/midi' }), fileName)
}

// Настоящий минимальный MIDI: гамма до мажор, темп 96 BPM.
function buildDemoMidi() {
  const notes = [60, 62, 64, 65, 67, 69, 71, 72]
  const track = [0x00, 0xff, 0x51, 0x03, 0x09, 0x89, 0x68] // темп: 625000 мкс на четверть
  for (const n of notes) {
    track.push(0x00, 0x90, n, 0x50) // note on
    track.push(0x81, 0x70, 0x80, n, 0x40) // через 240 тиков — note off
  }
  track.push(0x00, 0xff, 0x2f, 0x00) // конец трека
  const len = track.length
  return new Uint8Array([
    0x4d, 0x54, 0x68, 0x64, 0, 0, 0, 6, 0, 0, 0, 1, 0x01, 0xe0, // MThd, формат 0, 480 тиков
    0x4d, 0x54, 0x72, 0x6b, (len >>> 24) & 255, (len >>> 16) & 255, (len >>> 8) & 255, len & 255,
    ...track,
  ])
}

/* ───────────── Вспомогательное ───────────── */

function saveBlob(blob, fileName) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = fileName
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
