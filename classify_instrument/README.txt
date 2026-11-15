Для работы необходима программа FFmpeg
- Установка для WINDOWS
Всё одной командой в терминале
winget install "FFmpeg (Essentials Build)"
Либо ручной способ через скачивание
https://www.gyan.dev/ffmpeg/builds/
Название необходимого архива
ffmpeg-git-essentials.7z
Нужно сохранить или запомнить полный путь до папки с файлом ffmpeg.exe

После разархивирования необходимо добавить в систему
win → Измененение системых переменных среды → Переменные среды... → Переменные среды пользователя → Path → Изменить или нажать два раза на Path → Создать → Сохранённый ранее путь до файла ffmpeg.exe (путь нужно указать без файла ffmpeg.exe) → ОК

Необходима версия Python 3.11 (установка должна происходить от имени администратор)
winget install Python.Python.3.11

- Установка для macOS
Скачивание и установка программы через терминал
brew install ffmpeg
Скачивание и уставнока python
brew install python@3.11

- Установка для Linux
Скачивание и установка через терминал
sudo apt update
sudo apt install ffmpeg
Скачивание и установка python
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.11

Проверка
python --version
или при наличии Python Launcher
py -3.11 --version

Можно создать виртуальное окружение
python -m venv .venv
.\.venv\Scripts\activate.bat

Установка необходимых зависимостей для запуска
pip install uv
uv sync

Запуск
python app.py
или
fastapi dev app.py

Открывается по ссылке в браузере
http://127.0.0.1:8000/docs


Для выполнения скрипта classify_instrument.py необходимо создать папку videos_for_classify и поместить в неё видео формата .mp4
Для проверки необходим файл guitar_type.txt из ветки проекта под названием data
https://drive.google.com/drive/folders/102YC-IPFdMnfzcZAJYflD7F91dTkt501

Скрипт classify_instrument.py анализирует видео из папки videos_for_classify и производит проверку результатов на основе файла guitar_type.txt, если этот файл есть, а иначе скрипт выводит результаты анализов

Под Анализом имеется ввиду определение типа инструмента, используемого в видео

Логи запуска
(.venv) D:\python_programming\for_git_repositories\guitar-fingering-ai\classify_instrument>python classify_instrument.py
Список полученных файлов для обработки:
['videos_for_classify\\video_1.mp4', 'videos_for_classify\\video_10.mp4', 'videos_for_classify\\video_11.mp4', 'videos_for_classify\\video_12.mp4', 'videos_for_classify\\video_2.mp4', 'videos_for_classify\\video_3.mp4', 'videos_for_classify\\video_4.mp4', 'videos_for_classify\\video_5.mp4', 'videos_for_classify\\video_6.mp4', 'videos_for_classify\\video_7.mp4', 'videos_for_classify\\video_8.mp4', 'videos_for_classify\\video_9.mp4']
Loading weights: 100%|██████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 590/590 [00:00<00:00, 702.94it/s]
D:\python_programming\for_git_repositories\guitar-fingering-ai\classify_instrument\classify_instrument.py:192: UserWarning: Converting a tensor with requires_grad=True to a scalar may lead to unexpected behavior.
Consider using tensor.detach() first. (Triggered internally at C:\actions-runner\_work\pytorch\pytorch\torch\csrc\autograd\generated\python_variable_methods.cpp:821.)
  class_scores[cls] = class_scores.get(cls, 0.0) + float(prompt_probs[prompt_idx])

Результат анализа видео 'videos_for_classify\video_1.mp4':
Определен класс: electric (уверенность: 93%)
[h264 @ 0000018d87b39b40] Missing reference picture, default is 0
[h264 @ 0000018d87b39b40] decode_slice_header error

Результат анализа видео 'videos_for_classify\video_10.mp4':
Определен класс: acoustic (уверенность: 94%)
[h264 @ 0000018d8a71fec0] co located POCs unavailable
[h264 @ 0000018d8a720240] co located POCs unavailable
[h264 @ 0000018d8a71f000] co located POCs unavailable
[h264 @ 0000018d8a71fb00] co located POCs unavailable
...
[h264 @ 0000018d8990d700] co located POCs unavailable
[h264 @ 0000018d8990cc00] co located POCs unavailable
[h264 @ 0000018d8990d340] co located POCs unavailable

Результат анализа видео 'videos_for_classify\video_7.mp4':
Определен класс: classical (уверенность: 95%)

Результат анализа видео 'videos_for_classify\video_8.mp4':
Определен класс: electric (уверенность: 90%)

Результат анализа видео 'videos_for_classify\video_9.mp4':
Определен класс: electric (уверенность: 88%)
[OK] video_1: electric
[OK] video_10: acoustic
[OK] video_11: classical
[OK] video_12: electric
[OK] video_2: electric
[ERR] video_3: предсказано 'acoustic', ожидалось 'classical'
[OK] video_4: electric
[OK] video_5: classical
[OK] video_6: acoustic
[ERR] video_7: предсказано 'classical', ожидалось 'electric'
[OK] video_8: electric
[ERR] video_9: предсказано 'electric', ожидалось 'classical'

Общая точность (accuracy): 9/12 = 75.00%

========================================================================
Метрики по классам:
  Precision — точность предсказаний класса (доля верных среди всех,
              кому модель приписала этот класс)
  Recall    — per-class accuracy (сколько экземпляров класса нашлось)
========================================================================
Класс         Precision    Recall      F1   Support    TP    FP    FN
------------------------------------------------------------------------
acoustic         66.67%   100.00%    0.80         2     2     1     0
classical        66.67%    50.00%    0.57         4     2     1     2
electric         83.33%    83.33%    0.83         6     5     1     1
------------------------------------------------------------------------
macro avg        72.22%    77.78%    0.73        12
========================================================================

Confusion matrix (строки = ожидаемое, столбцы = предсказано):
              acoustic  classical   electric
acoustic             2          0          0
classical            1          2          1
electric             0          1          5
