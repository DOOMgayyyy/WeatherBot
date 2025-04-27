## запуск вирутального окружения

#`GismeteoTeleBot\Scripts\activate`


## выход из виртуального окружения

#deactivate
import telebot
from telebot import types
import requests
import os
import json
import time
import threading
import schedule
from datetime import datetime
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Инициализация бота
bot = telebot.TeleBot(os.getenv("TELEGRAM_TOKEN"))

# Конфигурация WeatherAPI
API_KEY = os.getenv("OWM_API_KEY")
BASE_URL = "http://api.weatherapi.com/v1/forecast.json"

# Словарь для хранения пользовательских настроек
user_settings = {}

# Путь к файлу для сохранения настроек
SETTINGS_FILE = "user_settings.json"

# Загрузка настроек пользователей при запуске
def load_user_settings():
    global user_settings
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as file:
                user_settings = json.load(file)
    except Exception as e:
        print(f"Ошибка при загрузке настроек: {e}")
        user_settings = {}

# Сохранение настроек пользователей
def save_user_settings():
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as file:
            json.dump(user_settings, file, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Ошибка при сохранении настроек: {e}")

# Функция получения погоды
def get_weather(city_name, days=1):
    try:
        params = {
            'q': city_name,
            'key': API_KEY,
            'days': days,
            'lang': 'ru',
            'aqi': 'no'
        }
        print(f"Отправляю запрос к API с параметрами: {params}")
        response = requests.get(BASE_URL, params=params)
        status = response.status_code
        print(f"Получен статус ответа: {status}")
       
        if status != 200:
            print(f"Ошибка API: {response.text}")
            return None
           
        return response.json()
    except Exception as e:
        print(f"Исключение при запросе API: {e}")
        return None

# Получение эмодзи по погодным условиям
def get_weather_emoji(condition_text):
    condition_lower = condition_text.lower()
    if 'дождь' in condition_lower or 'ливень' in condition_lower:
        if 'сильный' in condition_lower:
            return '🌧️'  # Сильный дождь
        elif 'небольшой' in condition_lower or 'слабый' in condition_lower:
            return '🌦️'  # Небольшой дождь
        else:
            return '🌧️'  # Обычный дождь
    elif 'снег' in condition_lower:
        return '❄️'  # Снег
    elif 'гроза' in condition_lower or 'гром' in condition_lower:
        return '⛈️'  # Гроза
    elif 'ясно' in condition_lower or 'солнечно' in condition_lower:
        return '☀️'  # Солнечно
    elif 'облачно' in condition_lower and ('частично' in condition_lower or 'переменная' in condition_lower):
        return '🌤️'  # Частично облачно
    elif 'облачно' in condition_lower:
        return '☁️'  # Облачно
    elif 'туман' in condition_lower or 'дымка' in condition_lower:
        return '🌫️'  # Туман
    else:
        return '🌡️'  # Общий случай

# Старт бота
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = str(message.from_user.id)
    
    # Удаляем сообщение пользователя с командой /start
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except Exception as e:
        print(f"Не удалось удалить сообщение пользователя: {e}")
    
    # Создаем настройки для нового пользователя, если их нет
    if user_id not in user_settings:
        user_settings[user_id] = {
            'city': '',
            'daily_forecast': False,
            'last_message_id': None
        }
        save_user_settings()
    
    # Главное меню
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button1 = types.KeyboardButton("Погода сейчас")
    button2 = types.KeyboardButton("Прогноз на день")
    button3 = types.KeyboardButton("Прогноз на 3 дня")
    button4 = types.KeyboardButton("Настройки⚙️")
    markup.add(button1, button2)
    markup.add(button3, button4)
    
    # Отправляем приветственное сообщение
    msg = bot.send_message(
        message.chat.id,
        "Привет! Я погодный бот. Выберите опцию или напишите название города:",
        reply_markup=markup
    )
    
    # Сохраняем ID сообщения для возможности его удаления
    user_settings[user_id]['last_message_id'] = msg.message_id
    save_user_settings()

# Обработка команды для установки города
@bot.message_handler(commands=['setcity'])
def set_city_command(message):
    bot.send_message(
        message.chat.id,
        "Пожалуйста, напишите название города, который хотите установить по умолчанию:"
    )
    bot.register_next_step_handler(message, save_city)

def save_city(message):
    user_id = str(message.from_user.id)
    city = message.text.strip()

    # Проверяем существование города
    weather_data = get_weather(city)
    if not weather_data:
        bot.send_message(
            message.chat.id,
            "Не удалось найти такой город. Пожалуйста, проверьте название и попробуйте снова."
        )
        return

    # Сохраняем город в настройках
    if user_id not in user_settings:
        user_settings[user_id] = {'city': city, 'daily_forecast': False, 'last_message_id': None}
    else:
        user_settings[user_id]['city'] = city

    save_user_settings()

    location = weather_data['location']

    # Удаляем старое сообщение
    if user_settings[user_id].get('last_message_id'):
        try:
            bot.delete_message(message.chat.id, user_settings[user_id]['last_message_id'])
        except Exception as e:
            print(f"Не удалось удалить предыдущее сообщение: {e}")

    # После установки города показываем главное меню с сообщением об успешной установке
    msg = bot.send_message(
        message.chat.id,
        f"Город {location['name']} ({location['country']}) установлен как ваш город по умолчанию.",
        reply_markup=main_menu_markup()
    )

    user_settings[user_id]['last_message_id'] = msg.message_id
    save_user_settings()

def main_menu_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        types.KeyboardButton("Погода сейчас"),
        types.KeyboardButton("Погода на сегодня"),
        types.KeyboardButton("Прогноз на 3 дня"),
        types.KeyboardButton("Настройки⚙️")
    )
    return markup


# Обработка текстовых сообщений
@bot.message_handler(content_types=['text'])
def handle_text(message):
    user_id = str(message.from_user.id)
    
    # Удаляем сообщение пользователя (если это разрешено API Telegram)
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except Exception as e:
        print(f"Не удалось удалить сообщение пользователя: {e}")
    
    if message.text == "Погода сейчас":
        if user_id in user_settings and user_settings[user_id]['city']:
            city = user_settings[user_id]['city']
            delete_last_bot_message(message.chat.id, user_id)
            send_current_weather(message, city)
        else:
            msg = bot.send_message(message.chat.id, "Пожалуйста, напишите название города:")
            user_settings[user_id]['last_message_id'] = msg.message_id
            save_user_settings()
            bot.register_next_step_handler(message, process_city_for_current)
    
    elif message.text == "Погода на сегодня":  # Изменено название кнопки
        if user_id in user_settings and user_settings[user_id]['city']:
            city = user_settings[user_id]['city']
            delete_last_bot_message(message.chat.id, user_id)

            send_day_forecast(message, city)
        else:
            msg = bot.send_message(message.chat.id, "Пожалуйста, напишите название города:")
            user_settings[user_id]['last_message_id'] = msg.message_id
            save_user_settings()
            bot.register_next_step_handler(message, process_city_for_day_forecast)
    
    elif message.text == "Прогноз на день":  # Оставляем поддержку старого названия для совместимости
        if user_id in user_settings and user_settings[user_id]['city']:
            city = user_settings[user_id]['city']
            delete_last_bot_message(message.chat.id, user_id)

            send_day_forecast(message, city)
        else:
            msg = bot.send_message(message.chat.id, "Пожалуйста, напишите название города:")
            user_settings[user_id]['last_message_id'] = msg.message_id
            save_user_settings()
            bot.register_next_step_handler(message, process_city_for_day_forecast)
    
    elif message.text == "Прогноз на 3 дня":
        if user_id in user_settings and user_settings[user_id]['city']:
            city = user_settings[user_id]['city']
            delete_last_bot_message(message.chat.id, user_id)
            send_three_day_forecast(message, city)
        else:
            msg = bot.send_message(message.chat.id, "Пожалуйста, напишите название города:")
            user_settings[user_id]['last_message_id'] = msg.message_id
            save_user_settings()
            bot.register_next_step_handler(message, process_city_for_three_days)
    
    elif message.text == "Настройки⚙️":
        delete_last_bot_message(message.chat.id, user_id)
        show_settings(message)
    
    elif message.text == "Установить город":
        msg = bot.send_message(message.chat.id, "Пожалуйста, напишите название города:")
        user_settings[user_id]['last_message_id'] = msg.message_id
        save_user_settings()
        delete_last_bot_message(message.chat.id, user_id)

        bot.register_next_step_handler(message, save_city)
    
    elif message.text == "Включить ежедневный прогноз":
        if user_id in user_settings and user_settings[user_id]['city']:
            user_settings[user_id]['daily_forecast'] = True
            save_user_settings()
            # После включения ежедневного прогноза показываем главное меню
            delete_last_bot_message(message.chat.id, user_id)

            show_main_menu_with_message(message, f"Ежедневный прогноз погоды в 6:00 включен для города {user_settings[user_id]['city']}.")
        else:
            msg = bot.send_message(
                message.chat.id,
                "Сначала нужно установить город по умолчанию. Пожалуйста, напишите название города:"
            )
            user_settings[user_id]['last_message_id'] = msg.message_id
            save_user_settings()
            delete_last_bot_message(message.chat.id, user_id)

            bot.register_next_step_handler(message, save_city_and_enable_daily)
    
    elif message.text == "Выключить ежедневный прогноз":
        user_settings[user_id]['daily_forecast'] = False
        save_user_settings()
        # После выключения ежедневного прогноза показываем главное меню
        show_main_menu_with_message(message, "Ежедневный прогноз погоды выключен.")
    
    elif message.text == "Вернуться в главное меню":
        show_main_menu(message)
    
    else:
        # Считаем, что пользователь ввел название города
        city = message.text.strip()
        delete_last_bot_message(message.chat.id, user_id)

        send_current_weather(message, city)

def process_city_for_current(message):
    city = message.text.strip()
    send_current_weather(message, city)

def process_city_for_day_forecast(message):
    city = message.text.strip()
    send_day_forecast(message, city)

def process_city_for_three_days(message):
    city = message.text.strip()
    send_three_day_forecast(message, city)

def save_city_and_enable_daily(message):
    user_id = str(message.from_user.id)
    city = message.text.strip()
    
    # Проверяем существование города
    weather_data = get_weather(city)
    if not weather_data:
        bot.send_message(
            message.chat.id,
            "Не удалось найти такой город. Пожалуйста, проверьте название и попробуйте снова."
        )
        return
    
    # Сохраняем город в настройках и включаем ежедневный прогноз
    if user_id not in user_settings:
        user_settings[user_id] = {'city': city, 'daily_forecast': True, 'last_message_id': None}
    else:
        user_settings[user_id]['city'] = city
        user_settings[user_id]['daily_forecast'] = True
    
    save_user_settings()
    
    location = weather_data['location']
    # После включения ежедневного прогноза показываем главное меню
    show_main_menu_with_message(
        message,
        f"Город {location['name']} ({location['country']}) установлен как ваш город по умолчанию.\n"
        f"Ежедневный прогноз погоды в 6:00 включен."
    )
def show_settings(message):
    user_id = str(message.from_user.id)
    
    # Удаляем старое сообщение
    delete_last_bot_message(message.chat.id, user_id)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("Установить город")
    if user_settings[user_id].get('daily_forecast', False):
        btn2 = types.KeyboardButton("Выключить ежедневный прогноз")
    else:
        btn2 = types.KeyboardButton("Включить ежедневный прогноз")
    back = types.KeyboardButton("Вернуться в главное меню")
    markup.add(btn1, btn2, back)
    
    settings_text = "Настройки:\n\n"
    if user_settings[user_id].get('city'):
        settings_text += f"Текущий город: {user_settings[user_id]['city']}\n"
    else:
        settings_text += "Текущий город: не установлен\n"
    settings_text += f"Ежедневный прогноз: {'Включен' if user_settings[user_id].get('daily_forecast', False) else 'Выключен'}"
    
    msg = bot.send_message(message.chat.id, settings_text, reply_markup=markup)
    
    user_settings[user_id]['last_message_id'] = msg.message_id
    save_user_settings()

# Главное меню с улучшенными названиями кнопок
def show_main_menu(message):
    user_id = str(message.from_user.id)
    
    # Главное меню
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button1 = types.KeyboardButton("Погода сейчас")
    button2 = types.KeyboardButton("Погода на сегодня")
    button3 = types.KeyboardButton("Прогноз на 3 дня")
    button4 = types.KeyboardButton("Настройки⚙️")
    markup.add(button1, button2)
    markup.add(button3, button4)
    
    # Удаляем предыдущее сообщение бота, если оно есть
    if user_id in user_settings and user_settings[user_id].get('last_message_id'):
        try:
            bot.delete_message(message.chat.id, user_settings[user_id]['last_message_id'])
        except Exception as e:
            print(f"Не удалось удалить сообщение: {e}")
    
    msg = bot.send_message(
        message.chat.id,
        "Главное меню",
        reply_markup=markup
    )
    
    # Сохраняем ID сообщения
    user_settings[user_id]['last_message_id'] = msg.message_id
    save_user_settings()

def delete_last_bot_message(chat_id, user_id):
    if user_id in user_settings and user_settings[user_id].get('last_message_id'):
        try:
            bot.delete_message(chat_id, user_settings[user_id]['last_message_id'])
        except Exception as e:
            print(f"Не удалось удалить сообщение: {e}")

def show_main_menu_with_message(message, text):
    user_id = str(message.from_user.id)
    
    # Главное меню
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button1 = types.KeyboardButton("Погода сейчас")
    button2 = types.KeyboardButton("Погода на сегодня")
    button3 = types.KeyboardButton("Прогноз на 3 дня")
    button4 = types.KeyboardButton("Настройки⚙️")
    markup.add(button1, button2)
    markup.add(button3, button4)
    
    # Удаляем предыдущее сообщение бота, если оно есть
    if user_id in user_settings and user_settings[user_id].get('last_message_id'):
        try:
            bot.delete_message(message.chat.id, user_settings[user_id]['last_message_id'])
        except Exception as e:
            print(f"Не удалось удалить сообщение: {e}")
    
    msg = bot.send_message(
        message.chat.id,
        text,
        reply_markup=markup
    )
    
    # Сохраняем ID сообщения
    user_settings[user_id]['last_message_id'] = msg.message_id
    save_user_settings()

def send_current_weather(message, city):
    user_id = str(message.from_user.id)
    
    # Удаляем предыдущее сообщение бота, если оно есть
    if user_id in user_settings and user_settings[user_id].get('last_message_id'):
        try:
            bot.delete_message(message.chat.id, user_settings[user_id]['last_message_id'])
        except Exception as e:
            print(f"Не удалось удалить сообщение: {e}")
    
    try:
        weather_data = get_weather(city)
        
        if not weather_data:
            # Создаем клавиатуру
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            button1 = types.KeyboardButton("Погода сейчас")
            button2 = types.KeyboardButton("Погода на сегодня")
            button3 = types.KeyboardButton("Прогноз на 3 дня")
            button4 = types.KeyboardButton("Настройки⚙️")
            markup.add(button1, button2)
            markup.add(button3, button4)
            
            msg = bot.send_message(message.chat.id, "Не удалось получить данные о погоде 😔", reply_markup=markup)
            user_settings[user_id]['last_message_id'] = msg.message_id
            save_user_settings()
            return
        
        # Парсинг данных
        current = weather_data['current']
        location = weather_data['location']
        
        temp = current['temp_c']
        feels_like = current['feelslike_c']
        humidity = current['humidity']
        wind_speed = current['wind_kph'] / 3.6  # Конвертация из км/ч в м/с
        description = current['condition']['text']
        
        # Получаем эмодзи
        weather_emoji = get_weather_emoji(description)
        
        response_text = (
            f"{weather_emoji} Сейчас погода в {location['name']} ({location['country']}):\n"
            f"{description}\n"
            f"🌡 Температура: {temp}°C (ощущается как {feels_like}°C)\n"
            f"💧 Влажность: {humidity}%\n"
            f"💨 Ветер: {wind_speed:.1f} м/с"
        )
        
        # Создаем клавиатуру
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        button1 = types.KeyboardButton("Погода сейчас")
        button2 = types.KeyboardButton("Погода на сегодня")
        button3 = types.KeyboardButton("Прогноз на 3 дня")
        button4 = types.KeyboardButton("Настройки⚙️")
        markup.add(button1, button2)
        markup.add(button3, button4)
        
        # Отправляем сообщение с клавиатурой
        msg = bot.send_message(message.chat.id, response_text, reply_markup=markup)
        
        # Сохраняем ID сообщения и город
        if user_id not in user_settings:
            user_settings[user_id] = {'city': city, 'daily_forecast': False, 'last_message_id': msg.message_id}
        else:
            user_settings[user_id]['last_message_id'] = msg.message_id
            # Сохраняем город только если он еще не был установлен
            if not user_settings[user_id].get('city'):
                user_settings[user_id]['city'] = city
        save_user_settings()
    
    except Exception as e:
        # Создаем клавиатуру в случае ошибки
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        button1 = types.KeyboardButton("Погода сейчас")
        button2 = types.KeyboardButton("Погода на сегодня")
        button3 = types.KeyboardButton("Прогноз на 3 дня")
        button4 = types.KeyboardButton("Настройки⚙️")
        markup.add(button1, button2)
        markup.add(button3, button4)
        
        msg = bot.send_message(message.chat.id, "Произошла ошибка, попробуйте ещё раз", reply_markup=markup)
        user_settings[user_id]['last_message_id'] = msg.message_id
        save_user_settings()
        print(f"Ошибка: {e}")

def send_day_forecast(message, city):
    user_id = str(message.from_user.id)
    
    # Удаляем предыдущее сообщение бота, если оно есть
    if user_id in user_settings and user_settings[user_id].get('last_message_id'):
        try:
            bot.delete_message(message.chat.id, user_settings[user_id]['last_message_id'])
        except Exception as e:
            print(f"Не удалось удалить сообщение: {e}")
    
    try:
        weather_data = get_weather(city, days=1)
        
        if not weather_data:
            # Создаем клавиатуру
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            button1 = types.KeyboardButton("Погода сейчас")
            button2 = types.KeyboardButton("Погода на сегодня")
            button3 = types.KeyboardButton("Прогноз на 3 дня")
            button4 = types.KeyboardButton("Настройки⚙️")
            markup.add(button1, button2)
            markup.add(button3, button4)
            
            msg = bot.send_message(message.chat.id, "Не удалось получить данные о погоде 😔", reply_markup=markup)
            user_settings[user_id]['last_message_id'] = msg.message_id
            save_user_settings()
            return
        
        # Парсинг данных
        forecast = weather_data['forecast']['forecastday'][0]
        location = weather_data['location']
        
        # Получаем данные по часам
        morning = next((hour for hour in forecast['hour'] if hour['time'].endswith('06:00')), None)
        noon = next((hour for hour in forecast['hour'] if hour['time'].endswith('12:00')), None)
        afternoon = next((hour for hour in forecast['hour'] if hour['time'].endswith('15:00')), None)
        evening = next((hour for hour in forecast['hour'] if hour['time'].endswith('18:00')), None)
        night = next((hour for hour in forecast['hour'] if hour['time'].endswith('00:00')), None)
        
        # Формируем текст прогноза
        date_str = datetime.strptime(forecast['date'], '%Y-%m-%d').strftime('%d.%m.%Y')
        
        response_text = f"🗓 Прогноз погоды на {date_str} для {location['name']} ({location['country']}):\n\n"
        
        if morning:
            morning_emoji = get_weather_emoji(morning['condition']['text'])
            response_text += (
                f"🌅 Утро (6:00): {morning_emoji} {morning['condition']['text']}\n"
                f"   🌡 {morning['temp_c']}°C, 💨 {morning['wind_kph']/3.6:.1f} м/с\n\n"
            )
        
        if noon:
            noon_emoji = get_weather_emoji(noon['condition']['text'])
            response_text += (
                f"🌞 День (12:00): {noon_emoji} {noon['condition']['text']}\n"
                f"   🌡 {noon['temp_c']}°C, 💨 {noon['wind_kph']/3.6:.1f} м/с\n\n"
            )
        
        if afternoon:
            afternoon_emoji = get_weather_emoji(afternoon['condition']['text'])
            response_text += (
                f"🕒 После обеда (15:00): {afternoon_emoji} {afternoon['condition']['text']}\n"
                f"   🌡 {afternoon['temp_c']}°C, 💨 {afternoon['wind_kph']/3.6:.1f} м/с\n\n"
            )
        
        if evening:
            evening_emoji = get_weather_emoji(evening['condition']['text'])
            response_text += (
                f"🌆 Вечер (18:00): {evening_emoji} {evening['condition']['text']}\n"
                f"   🌡 {evening['temp_c']}°C, 💨 {evening['wind_kph']/3.6:.1f} м/с\n\n"
            )
        
        if night:
            night_emoji = get_weather_emoji(night['condition']['text'])
            response_text += (
                f"🌙 Ночь (00:00): {night_emoji} {night['condition']['text']}\n"
                f"   🌡 {night['temp_c']}°C, 💨 {night['wind_kph']/3.6:.1f} м/с\n\n"
            )
        
        # Общая информация за день
        day = forecast['day']
        response_text += (
            f"📊 В целом за день:\n"
            f"   Мин. температура: {day['mintemp_c']}°C\n"
            f"   Макс. температура: {day['maxtemp_c']}°C\n"
            f"   Средняя температура: {day['avgtemp_c']}°C\n"
            f"   Вероятность осадков: {day['daily_chance_of_rain']}%\n"
        )
        
        # Создаем клавиатуру
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        button1 = types.KeyboardButton("Погода сейчас")
        button2 = types.KeyboardButton("Погода на сегодня")
        button3 = types.KeyboardButton("Прогноз на 3 дня")
        button4 = types.KeyboardButton("Настройки⚙️")
        markup.add(button1, button2)
        markup.add(button3, button4)
        
        # Отправляем сообщение с клавиатурой
        msg = bot.send_message(message.chat.id, response_text, reply_markup=markup)
        
        # Сохраняем ID сообщения и город
        if user_id not in user_settings:
            user_settings[user_id] = {'city': city, 'daily_forecast': False, 'last_message_id': msg.message_id}
        else:
            user_settings[user_id]['last_message_id'] = msg.message_id
            # Сохраняем город только если он еще не был установлен
            if not user_settings[user_id].get('city'):
                user_settings[user_id]['city'] = city
        save_user_settings()
    
    except Exception as e:
        # Создаем клавиатуру в случае ошибки
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        button1 = types.KeyboardButton("Погода сейчас")
        button2 = types.KeyboardButton("Погода на сегодня")
        button3 = types.KeyboardButton("Прогноз на 3 дня")
        button4 = types.KeyboardButton("Настройки⚙️")
        markup.add(button1, button2)
        markup.add(button3, button4)
        
        msg = bot.send_message(message.chat.id, "Произошла ошибка, попробуйте ещё раз", reply_markup=markup)
        user_settings[user_id]['last_message_id'] = msg.message_id
        save_user_settings()
        print(f"Ошибка: {e}")

def send_three_day_forecast(message, city):
    user_id = str(message.from_user.id)
    
    # Удаляем предыдущее сообщение бота, если оно есть
    if user_id in user_settings and user_settings[user_id].get('last_message_id'):
        try:
            bot.delete_message(message.chat.id, user_settings[user_id]['last_message_id'])
        except Exception as e:
            print(f"Не удалось удалить сообщение: {e}")
    
    try:
        weather_data = get_weather(city, days=3)
        
        if not weather_data:
            # Создаем клавиатуру
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            button1 = types.KeyboardButton("Погода сейчас")
            button2 = types.KeyboardButton("Погода на сегодня")
            button3 = types.KeyboardButton("Прогноз на 3 дня")
            button4 = types.KeyboardButton("Настройки⚙️")
            markup.add(button1, button2)
            markup.add(button3, button4)
            
            msg = bot.send_message(message.chat.id, "Не удалось получить данные о погоде 😔", reply_markup=markup)
            user_settings[user_id]['last_message_id'] = msg.message_id
            save_user_settings()
            return
        
        # Парсинг данных
        forecast_days = weather_data['forecast']['forecastday']
        location = weather_data['location']
        
        response_text = f"🗓 Прогноз погоды на 3 дня для {location['name']} ({location['country']}):\n\n"
        
        # Проходим по всем дням прогноза
        for forecast in forecast_days:
            date = datetime.strptime(forecast['date'], '%Y-%m-%d')
            date_str = date.strftime('%d.%m.%Y')
            day_name = date.strftime('%A')
            
            # Переводим название дня недели на русский
            days_ru = {
                'Monday': 'Понедельник',
                'Tuesday': 'Вторник',
                'Wednesday': 'Среда',
                'Thursday': 'Четверг',
                'Friday': 'Пятница',
                'Saturday': 'Суббота',
                'Sunday': 'Воскресенье'
            }
            day_name_ru = days_ru.get(day_name, day_name)
            
            day = forecast['day']
            condition = day['condition']['text']
            condition_emoji = get_weather_emoji(condition)
            
            response_text += (
                f"📅 {day_name_ru}, {date_str}:\n"
                f"   {condition_emoji} {condition}\n"
                f"   🌡 {day['mintemp_c']}°C - {day['maxtemp_c']}°C (средняя: {day['avgtemp_c']}°C)\n"
                f"   💨 Макс. скорость ветра: {day['maxwind_kph']/3.6:.1f} м/с\n"
                f"   💧 Вероятность осадков: {day['daily_chance_of_rain']}%\n\n"
            )
        
        # Создаем клавиатуру
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        button1 = types.KeyboardButton("Погода сейчас")
        button2 = types.KeyboardButton("Погода на сегодня")
        button3 = types.KeyboardButton("Прогноз на 3 дня")
        button4 = types.KeyboardButton("Настройки⚙️")
        markup.add(button1, button2)
        markup.add(button3, button4)
        
        # Отправляем сообщение с клавиатурой
        msg = bot.send_message(message.chat.id, response_text, reply_markup=markup)
        
        # Сохраняем ID сообщения и город
        if user_id not in user_settings:
            user_settings[user_id] = {'city': city, 'daily_forecast': False, 'last_message_id': msg.message_id}
        else:
            user_settings[user_id]['last_message_id'] = msg.message_id
            # Сохраняем город только если он еще не был установлен
            if not user_settings[user_id].get('city'):
                user_settings[user_id]['city'] = city
        save_user_settings()
    
    except Exception as e:
        # Создаем клавиатуру в случае ошибки
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        button1 = types.KeyboardButton("Погода сейчас")
        button2 = types.KeyboardButton("Погода на сегодня")
        button3 = types.KeyboardButton("Прогноз на 3 дня")
        button4 = types.KeyboardButton("Настройки⚙️")
        markup.add(button1, button2)
        markup.add(button3, button4)
        
        msg = bot.send_message(message.chat.id, "Произошла ошибка, попробуйте ещё раз", reply_markup=markup)
        user_settings[user_id]['last_message_id'] = msg.message_id
        save_user_settings()
        print(f"Ошибка: {e}")

def send_day_forecast(message, city):
    user_id = str(message.from_user.id)
    
    try:
        weather_data = get_weather(city, days=1)
        
        if not weather_data:
            # Создаем клавиатуру заново
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            button1 = types.KeyboardButton("Погода сейчас")
            button2 = types.KeyboardButton("Прогноз на день")
            button3 = types.KeyboardButton("Прогноз на 3 дня")
            button4 = types.KeyboardButton("Настройки⚙️")
            markup.add(button1, button2)
            markup.add(button3, button4)
            
            msg = bot.send_message(message.chat.id, "Не удалось получить данные о погоде 😔", reply_markup=markup)
            user_settings[user_id]['last_message_id'] = msg.message_id
            save_user_settings()
            return
        
        # Парсинг данных
        forecast = weather_data['forecast']['forecastday'][0]
        location = weather_data['location']
        
        # Получаем данные по часам (утро, день, вечер, ночь)
        # Утро (6:00)
        morning = next((hour for hour in forecast['hour'] if hour['time'].endswith('06:00')), None)
        # День (12:00)
        noon = next((hour for hour in forecast['hour'] if hour['time'].endswith('12:00')), None)
        # День (15:00)
        afternoon = next((hour for hour in forecast['hour'] if hour['time'].endswith('15:00')), None)
        # Вечер (18:00)
        evening = next((hour for hour in forecast['hour'] if hour['time'].endswith('18:00')), None)
        # Ночь (00:00)
        night = next((hour for hour in forecast['hour'] if hour['time'].endswith('00:00')), None)
        
        # Формируем текст прогноза
        date_str = datetime.strptime(forecast['date'], '%Y-%m-%d').strftime('%d.%m.%Y')
        
        response_text = f"🗓 Прогноз погоды на {date_str} для {location['name']} ({location['country']}):\n\n"
        
        if morning:
            morning_emoji = get_weather_emoji(morning['condition']['text'])
            response_text += (
                f"🌅 Утро (6:00): {morning_emoji} {morning['condition']['text']}\n"
                f"   🌡 {morning['temp_c']}°C, 💨 {morning['wind_kph']/3.6:.1f} м/с\n\n"
            )
        
        if noon:
            noon_emoji = get_weather_emoji(noon['condition']['text'])
            response_text += (
                f"🌞 День (12:00): {noon_emoji} {noon['condition']['text']}\n"
                f"   🌡 {noon['temp_c']}°C, 💨 {noon['wind_kph']/3.6:.1f} м/с\n\n"
            )
        
        if afternoon:
            afternoon_emoji = get_weather_emoji(afternoon['condition']['text'])
            response_text += (
                f"🕒 После обеда (15:00): {afternoon_emoji} {afternoon['condition']['text']}\n"
                f"   🌡 {afternoon['temp_c']}°C, 💨 {afternoon['wind_kph']/3.6:.1f} м/с\n\n"
            )
        
        if evening:
            evening_emoji = get_weather_emoji(evening['condition']['text'])
            response_text += (
                f"🌆 Вечер (18:00): {evening_emoji} {evening['condition']['text']}\n"
                f"   🌡 {evening['temp_c']}°C, 💨 {evening['wind_kph']/3.6:.1f} м/с\n\n"
            )
        
        if night:
            night_emoji = get_weather_emoji(night['condition']['text'])
            response_text += (
                f"🌙 Ночь (00:00): {night_emoji} {night['condition']['text']}\n"
                f"   🌡 {night['temp_c']}°C, 💨 {night['wind_kph']/3.6:.1f} м/с\n\n"
            )
        
        # Общая информация за день
        day = forecast['day']
        response_text += (
            f"📊 В целом за день:\n"
            f"   Мин. температура: {day['mintemp_c']}°C\n"
            f"   Макс. температура: {day['maxtemp_c']}°C\n"
            f"   Средняя температура: {day['avgtemp_c']}°C\n"
            f"   Вероятность осадков: {day['daily_chance_of_rain']}%\n"
        )
        
        # Создаем клавиатуру заново
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        button1 = types.KeyboardButton("Погода сейчас")
        button2 = types.KeyboardButton("Прогноз на день")
        button3 = types.KeyboardButton("Прогноз на 3 дня")
        button4 = types.KeyboardButton("Настройки⚙️")
        markup.add(button1, button2)
        markup.add(button3, button4)
        
        # Отправляем сообщение с клавиатурой
        msg = bot.send_message(message.chat.id, response_text, reply_markup=markup)
        
        # Сохраняем ID сообщения и город
        if user_id not in user_settings:
            user_settings[user_id] = {'city': city, 'daily_forecast': False, 'last_message_id': msg.message_id}
        else:
            user_settings[user_id]['last_message_id'] = msg.message_id
            # Сохраняем город только если он еще не был установлен
            if not user_settings[user_id].get('city'):
                user_settings[user_id]['city'] = city
        save_user_settings()
    
    except Exception as e:
        # Создаем клавиатуру заново в случае ошибки
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        button1 = types.KeyboardButton("Погода сейчас")
        button2 = types.KeyboardButton("Прогноз на день")
        button3 = types.KeyboardButton("Прогноз на 3 дня")
        button4 = types.KeyboardButton("Настройки⚙️")
        markup.add(button1, button2)
        markup.add(button3, button4)
        
        msg = bot.send_message(message.chat.id, "Произошла ошибка, попробуйте ещё раз", reply_markup=markup)
        user_settings[user_id]['last_message_id'] = msg.message_id
        save_user_settings()
        print(f"Ошибка: {e}")

def send_three_day_forecast(message, city):

    user_id = str(message.from_user.id)
    delete_last_bot_message(message.chat.id, user_id)

    try:
        weather_data = get_weather(city, days=3)
        
        if not weather_data:
            # Создаем клавиатуру заново
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            button1 = types.KeyboardButton("Погода сейчас")
            button2 = types.KeyboardButton("Прогноз на день")
            button3 = types.KeyboardButton("Прогноз на 3 дня")
            button4 = types.KeyboardButton("Настройки⚙️")
            markup.add(button1, button2)
            markup.add(button3, button4)
            
            msg = bot.send_message(message.chat.id, "Не удалось получить данные о погоде 😔", reply_markup=markup)
            user_settings[user_id]['last_message_id'] = msg.message_id
            save_user_settings()
            return
        
        # Парсинг данных
        forecast_days = weather_data['forecast']['forecastday']
        location = weather_data['location']
        
        response_text = f"🗓 Прогноз погоды на 3 дня для {location['name']} ({location['country']}):\n\n"
        
        # Проходим по всем дням прогноза
        for forecast in forecast_days:
            date = datetime.strptime(forecast['date'], '%Y-%m-%d')
            date_str = date.strftime('%d.%m.%Y')
            day_name = date.strftime('%A')
            
            # Переводим название дня недели на русский
            days_ru = {
                'Monday': 'Понедельник',
                'Tuesday': 'Вторник',
                'Wednesday': 'Среда',
                'Thursday': 'Четверг',
                'Friday': 'Пятница',
                'Saturday': 'Суббота',
                'Sunday': 'Воскресенье'
            }
            day_name_ru = days_ru.get(day_name, day_name)
            
            day = forecast['day']
            condition = day['condition']['text']
            condition_emoji = get_weather_emoji(condition)
            
            response_text += (
                f"📅 {day_name_ru}, {date_str}:\n"
                f"   {condition_emoji} {condition}\n"
                f"   🌡 {day['mintemp_c']}°C - {day['maxtemp_c']}°C (средняя: {day['avgtemp_c']}°C)\n"
                f"   💨 Макс. скорость ветра: {day['maxwind_kph']/3.6:.1f} м/с\n"
                f"   💧 Вероятность осадков: {day['daily_chance_of_rain']}%\n\n"
            )
        
        # Создаем клавиатуру заново
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        button1 = types.KeyboardButton("Погода сейчас")
        button2 = types.KeyboardButton("Прогноз на день")
        button3 = types.KeyboardButton("Прогноз на 3 дня")
        button4 = types.KeyboardButton("Настройки⚙️")
        markup.add(button1, button2)
        markup.add(button3, button4)
        
        # Отправляем сообщение с клавиатурой
        msg = bot.send_message(message.chat.id, response_text, reply_markup=markup)
        
        # Сохраняем ID сообщения и город
        if user_id not in user_settings:
            user_settings[user_id] = {'city': city, 'daily_forecast': False, 'last_message_id': msg.message_id}
        else:
            user_settings[user_id]['last_message_id'] = msg.message_id
            # Сохраняем город только если он еще не был установлен
            if not user_settings[user_id].get('city'):
                user_settings[user_id]['city'] = city
        save_user_settings()
    
    except Exception as e:
        # Создаем клавиатуру заново в случае ошибки
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        button1 = types.KeyboardButton("Погода сейчас")
        button2 = types.KeyboardButton("Прогноз на день")
        button3 = types.KeyboardButton("Прогноз на 3 дня")
        button4 = types.KeyboardButton("Настройки⚙️")
        markup.add(button1, button2)
        markup.add(button3, button4)
        
        msg = bot.send_message(message.chat.id, "Произошла ошибка, попробуйте ещё раз", reply_markup=markup)
        user_settings[user_id]['last_message_id'] = msg.message_id
        save_user_settings()
        print(f"Ошибка: {e}")

# Функция для отправки ежедневного прогноза всем пользователям, которые его включили
def send_daily_forecasts():
    print("Запуск функции отправки ежедневных прогнозов")
    for user_id, settings in user_settings.items():
        if settings.get('daily_forecast') and settings.get('city'):
            try:
                chat_id = int(user_id)
                city = settings['city']
                weather_data = get_weather(city, days=1)
                
                if not weather_data:
                    bot.send_message(chat_id, f"Не удалось получить данные о погоде для {city} 😔")
                    continue
                
                # Формируем текст прогноза на день
                forecast = weather_data['forecast']['forecastday'][0]
                location = weather_data['location']
                day = forecast['day']
                condition = day['condition']['text']
                condition_emoji = get_weather_emoji(condition)
                
                date_str = datetime.strptime(forecast['date'], '%Y-%m-%d').strftime('%d.%m.%Y')
                
                response_text = (
                    f"🔔 Доброе утро! Прогноз погоды на {date_str} для {location['name']} ({location['country']}):\n\n"
                    f"{condition_emoji} {condition}\n"
                    f"🌡 Температура: {day['mintemp_c']}°C - {day['maxtemp_c']}°C (средняя: {day['avgtemp_c']}°C)\n"
                    f"💨 Макс. скорость ветра: {day['maxwind_kph']/3.6:.1f} м/с\n"
                    f"💧 Вероятность осадков: {day['daily_chance_of_rain']}%\n"
                )
                
                # Получаем данные по часам (утро, день, вечер)
                morning = next((hour for hour in forecast['hour'] if hour['time'].endswith('06:00')), None)
                noon = next((hour for hour in forecast['hour'] if hour['time'].endswith('12:00')), None)
                evening = next((hour for hour in forecast['hour'] if hour['time'].endswith('18:00')), None)
                
                if morning:
                    morning_emoji = get_weather_emoji(morning['condition']['text'])
                    response_text += f"\n🌅 Утро (6:00): {morning_emoji} {morning['temp_c']}°C, {morning['condition']['text']}"
                
                if noon:
                    noon_emoji = get_weather_emoji(noon['condition']['text'])
                    response_text += f"\n🌞 День (12:00): {noon_emoji} {noon['temp_c']}°C, {noon['condition']['text']}"
                
                if evening:
                    evening_emoji = get_weather_emoji(evening['condition']['text'])
                    response_text += f"\n🌆 Вечер (18:00): {evening_emoji} {evening['temp_c']}°C, {evening['condition']['text']}"
                
                # Отправляем прогноз
                bot.send_message(chat_id, response_text)
                print(f"Отправлен ежедневный прогноз пользователю {user_id}")
            except Exception as e:
                print(f"Ошибка при отправке ежедневного прогноза пользователю {user_id}: {e}")

# Планировщик для отправки ежедневных прогнозов
def schedule_daily_forecasts():
    schedule.every().day.at("06:00").do(send_daily_forecasts)
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # Проверка каждую минуту

# Запуск планировщика в отдельном потоке
def start_scheduler():
    scheduler_thread = threading.Thread(target=schedule_daily_forecasts)
    scheduler_thread.daemon = True
    scheduler_thread.start()

if __name__ == "__main__":
    print("Бот запущен. Нажмите Ctrl+C для остановки")
    try:
        # Загружаем настройки пользователей
        load_user_settings()
        
        # Запускаем планировщик
        start_scheduler()
        
        # Запускаем бота
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"Критическая ошибка бота: {e}")