import { useEffect, useRef, useState } from 'react'
import { uploadVideo, getStatus, downloadResult, USE_MOCK } from './api.js'
import { validateFile, MAX_SIZE_MB } from './validate.js'
import {
  CloudUploadIcon, ScanIcon, NoteIcon, NotesIcon,
  CheckBadge, PlayBadge, ClockBadge, SpinnerIcon,
  CrossCircleIcon, DownloadIcon, UploadArrowIcon,
} from './icons.jsx'
import './styles.css'

const POLL_MS = 1500
const MAX_POLL_FAILS = 3

const STEPS = [
  { label: 'Загрузка видео', Icon: CloudUploadIcon },
  { label: 'Ожидание в очереди', Icon: ScanIcon },
  { label: 'Извлечение звука', Icon: NoteIcon },
  { label: 'Формирование MIDI', Icon: NotesIcon },
]

const BADGES = { done: CheckBadge, current: PlayBadge, waiting: ClockBadge }
const STATUS_TEXT = { done: 'выполнено', current: 'выполняется', waiting: 'ожидает' }

export default function App() {
  const [s, setS] = useState({ phase: 'idle' })
  const [downloadError, setDownloadError] = useState(null)
  const [downloading, setDownloading] = useState(false)
  const runId = useRef(0)

  async function handleFile(file) {
    const run = ++runId.current
    setDownloadError(null)

    const problem = validateFile(file)
    if (problem) {
      setS({ phase: 'error', error: problem })
      return
    }

    const baseName = file.name.replace(/\.[^.]+$/, '') || 'result'
    setS({ phase: 'uploading', progress: 0, baseName })
    try {
      const { taskId } = await uploadVideo(file, (progress) => {
        if (run === runId.current) setS((p) => (p.phase === 'uploading' ? { ...p, progress } : p))
      })
      if (run !== runId.current) return
      setS({ phase: 'processing', taskId, stage: 1, baseName })
    } catch (e) {
      if (run !== runId.current) return
      setS({ phase: 'error', error: { title: 'Не удалось загрузить видео', text: e.message } })
    }
  }

  useEffect(() => {
    if (s.phase !== 'processing') return
    const { taskId, baseName } = s
    let stopped = false
    let timer
    let fails = 0

    const tick = async () => {
      try {
        const st = await getStatus(taskId)
        if (stopped) return
        fails = 0
        if (st.status === 'done') {
          setS({ phase: 'done', taskId, baseName, tempo: st.tempo, instrument: st.instrument })
        } else if (st.status === 'error') {
          setS({
            phase: 'error',
            error: {
              title: 'Не удалось обработать видео',
              text: st.message || 'Что-то пошло не так на сервере. Попробуйте загрузить другой файл.',
            },
          })
        } else {
          setS((p) => (p.phase === 'processing' ? { ...p, stage: st.stage } : p))
          timer = setTimeout(tick, POLL_MS)
        }
      } catch (e) {
        if (stopped) return
        if (++fails >= MAX_POLL_FAILS) {
          setS({ phase: 'error', error: { title: 'Не удалось получить результат', text: e.message } })
        } else {
          timer = setTimeout(tick, POLL_MS)
        }
      }
    }
    tick()
    return () => {
      stopped = true
      clearTimeout(timer)
    }
  }, [s.phase, s.taskId])

  async function handleDownload() {
    setDownloadError(null)
    setDownloading(true)
    try {
      await downloadResult(s.taskId, `${s.baseName}.mid`)
    } catch (e) {
      setDownloadError(e.message)
    } finally {
      setDownloading(false)
    }
  }

  function reset() {
    runId.current++
    setDownloadError(null)
    setS({ phase: 'idle' })
  }

  return (
    <main className="page">

      {(s.phase === 'idle' || s.phase === 'error') && (
        <UploadScreen error={s.phase === 'error' ? s.error : null} onFile={handleFile} />
      )}
      {(s.phase === 'uploading' || s.phase === 'processing') && <ProgressScreen s={s} />}
      {s.phase === 'done' && (
        <ResultScreen
          s={s}
          onDownload={handleDownload}
          downloading={downloading}
          downloadError={downloadError}
          onReset={reset}
        />
      )}
    </main>
  )
}


function UploadScreen({ error, onFile }) {
  const inputRef = useRef(null)
  const [dragging, setDragging] = useState(false)

  const pick = (files) => {
    if (files && files[0]) onFile(files[0])
  }

  return (
    <section className="screen">
      {error ? (
        <div className="error-banner" role="alert">
          <CrossCircleIcon className="error-banner__icon" />
          <p className="error-banner__text">
            <strong>{error.title}</strong>
            <span>{error.text}</span>
          </p>
        </div>
      ) : (
        <h1 className="title">Загрузите видео со своего устройства:</h1>
      )}

      <div
        className={`dropzone${dragging ? ' dropzone--drag' : ''}`}
        role="button"
        tabIndex={0}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            inputRef.current?.click()
          }
        }}
        onDragOver={(e) => {
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragging(false)
          pick(e.dataTransfer.files)
        }}
      >
        <UploadArrowIcon className="dropzone__icon" />
        <p className="dropzone__text">Перетащите файл сюда или нажмите, чтобы загрузить с устройства (mp4, mov)</p>
        <p className="dropzone__hint">Максимальный размер файла: {MAX_SIZE_MB} МБ</p>
        <input
          ref={inputRef}
          type="file"
          accept=".mp4,.mov,video/mp4,video/quicktime"
          hidden
          onChange={(e) => {
            pick(e.target.files)
            e.target.value = ''
          }}
        />
      </div>
    </section>
  )
}


function ProgressScreen({ s }) {
  const current = s.phase === 'uploading' ? 0 : s.stage
  const uploading = s.phase === 'uploading'

  return (
    <section className="screen screen--progress">
      <h1 className="title" role="status">
        {uploading ? 'Загружаем видео, подождите...' : 'Ваш файл обрабатывается, подождите...'}
      </h1>

      <ol className="steps">
        {STEPS.map((step, i) => {
          const status = i < current ? 'done' : i === current ? 'current' : 'waiting'
          const Badge = BADGES[status]
          return (
            <li key={step.label} className={`step step--${status}`} aria-current={status === 'current' ? 'step' : undefined}>
              <div className="step__icon">
                <step.Icon />
                <span className="step__badge"><Badge /></span>
              </div>
              <span className="step__label">
                {step.label}
                <span className="visually-hidden"> — {STATUS_TEXT[status]}</span>
              </span>
            </li>
          )
        })}
      </ol>

      {uploading ? (
        <div className="upload-progress">
          <div
            className="upload-progress__bar"
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={s.progress}
            aria-label="Загрузка видео"
          >
            <div className="upload-progress__fill" style={{ width: `${s.progress}%` }} />
          </div>
          <span className="upload-progress__value">{s.progress}%</span>
        </div>
      ) : (
        <SpinnerIcon className="spinner" />
      )}
    </section>
  )
}


function ResultScreen({ s, onDownload, downloading, downloadError, onReset }) {
  const facts = [
    s.tempo != null && `Темп: ${s.tempo} BPM`,
    s.instrument && `Инструмент: ${s.instrument}`,
  ].filter(Boolean)

  return (
    <section className="screen">
      <h1 className="title title--result" role="status">Результат готов!</h1>

      {facts.length > 0 && (
        <ul className="facts">
          {facts.map((f) => (
            <li key={f} className="fact">{f}</li>
          ))}
        </ul>
      )}

      <div className="actions">
        <button className="btn btn--primary" onClick={onDownload} disabled={downloading}>
          <span>{downloading ? 'Скачиваем...' : 'Скачать .mid'}</span>
          <DownloadIcon className="btn__icon" />
        </button>
        <button className="btn btn--secondary" onClick={onReset}>Загрузить другой файл</button>
        {downloadError && <p className="inline-error" role="alert">{downloadError}</p>}
      </div>
    </section>
  )
}
