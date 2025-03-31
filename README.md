# Описание проекта
Данный проект направлен на создание Telegram-бота для взаимодействия клиентов с автосервисом, который облегчит процесс записи в автосервис, предоставит удобный функционал для клиентов и работников автосервиса, соберет статистику, а также предоставит возможность уведомления пользователей о запланированном посещении автосервиса.


## Содержание
- [Цели проекта](#цели-проекта)

- [Функционал](#функционал)

- [Используемые технологии](#используемые-технологии)

- [Запуск Telegram-бота](#запуск-telegram-бота)


## Цели проекта
- Запись в автосервис

- Просмотр и управление записями, сохраненными в базе данных

- Управлнение расписанием рабочего времени сотрудников

- Управление данными пользователей

- Сбор статистики предоставленных услуг

- Уведомление пользователей о записи

## Функционал
Телеграмм-бот предоставляет функционал для клиентов и администраторов автосервиса


- **Функционал клиента**
  1. Запись на услугу

  2. Отмена созданной записи

  3. Просмотр свободного времени для записи

  4. Просмотр запланированных посещений автосервиса 

  5. Уведомление клиента о записи за 2 часа

  6. Выход из профиля


- **Функционал администратора**
  1. Управление записями (добавление, удаление)

  2. Управление пользователями (добавление, удаление, изменение данных)

  3. Изменение информации о предоставляемых услугах

  4. Просмотр информации о клиентах и их записях

  5. Просмотр информации о сотрудниках (время работы, статус в данный момент)
  
  6. Просмотр расписания услуг через Яндекс календарь
  
  7. Сбор статистики за промежуток

- **Сценарии работы Telegram-бота**
!['uml'](/info_files/UML.png)
  
## Используемые технологии

- **Telegram-бот**(Aiogram) - интерфейс для пользователя

- **Aiogram_calendar** - предоставление календаря в чате для выбора даты

- **Aiohttp** - создание асинхронных HTTP-запросов для взаимодействия с Яндекс календарем
- 
- **AsyncIOScheduler** - планировщик уведомлений польлзователей о визите в автосервис

- **Реляционная база данных** - хранение информации о пользователях, записях и информации о сотрудниках
 
  Структура базы данных:
    !['df'](/info_files/database.png)
   
- **Asyncpg** - библиотека Python для взаимодействия с базой данных

## Запуск Telegram-бота
1. Установка зависимостей
  
    Создаем виртуальное окружение venv \
    ```python -m venv /path/to/new/virtual/myenv```\
    ```source myenv/bin/activate```\
    Загрузка необходимых библиотек с использованием файла с описанием библиотек \
    ```pip install -r requirements.txt``` 

2. Конфигурация бота и базы данных

    В файле .env сохранен токен тг-бота, пароль для базы данных и Яндекс аккаунта, в файле config.py дополнительная информация о базе данных, Telegram-боте и Яндекс календаре

3. Запуск бота

    Для запуска бота необходимо запустить файл bot.py командой ```python3 bot.py```, логгирование, встроенное в Aiogram выводится в консоль