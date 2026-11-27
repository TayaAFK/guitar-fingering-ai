# guitar-fingering-ai
**Распознавание гитарной аппликатуры по видео с использованием ИИ**

## О проекте

Учебный проект по заданию **ООО «Цифровые решения»**. Сервис принимает видео с игрой на гитаре (файл или ссылку на видеохостинг), распознаёт аппликатуру музыканта и сохраняет результат в виде MIDI-файла.

**Цель:** создать работающее MVP-приложение, которое по видео определяет тип гитары и переводит игру музыканта в нотную форму (MIDI).

## Требования
- Python 3.10+
- pip / poetry

## Установка окружения

1. Клонируйте репозиторий:
   git clone <repository_url>
   cd guitar_vision_module

2. Создайте и активируйте виртуальное окружение:
   python -m venv .venv
   .venv\Scripts\activate для Windows

3. Установите зависимости:
   pip install -r requirements.txt

4. Скачайте модель MediaPipe, neck в корневую папку или в data/:
- В models/ https://drive.google.com/file/d/1s8cEoTl88kWrPJCUaGKeumwDJ1IhCzgQ/view?usp=sharing
- В data/ hand_landmarker.task https://drive.google.com/file/d/1Gn0teBQqpinfWgsEH3c5G4uVVMpt5vjG/view?usp=sharing
- Положите тестовые видео в папку data/.
   
