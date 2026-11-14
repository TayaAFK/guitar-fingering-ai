// Проверка файла на стороне браузера: только .mp4 и .mov, не больше 500 МБ.

export const ALLOWED_EXTENSIONS = ['mp4', 'mov']
export const MAX_SIZE_MB = 500
const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024

/** Возвращает null, если файл подходит, иначе { title, text } для баннера ошибки. */
export function validateFile(file) {
  const ext = file.name.includes('.') ? file.name.split('.').pop().toLowerCase() : ''
  if (!ALLOWED_EXTENSIONS.includes(ext)) {
    return {
      title: 'Не удалось загрузить видео',
      text: 'Этот формат не поддерживается. Загрузите файл в формате MP4 или MOV.',
    }
  }
  if (file.size > MAX_SIZE_BYTES) {
    return {
      title: 'Не удалось загрузить видео',
      text: `Файл слишком большой. Максимальный размер — ${MAX_SIZE_MB} МБ.`,
    }
  }
  if (file.size === 0) {
    return {
      title: 'Не удалось загрузить видео',
      text: 'Файл пустой. Выберите другое видео.',
    }
  }
  return null
}
