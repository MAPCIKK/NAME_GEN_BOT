import telebot
import sqlite3
import logging
from DB import *
from validators import *
from GPT import *
token = 'YOUR_BOT_TOKEN'
bot = telebot.TeleBot(token)
create_database()
LOGS = 'logs.txt'
# настраиваем запись логов в файл
logging.basicConfig(filename=LOGS, level=logging.INFO,
                    format="%(asctime)s FILE: %(filename)s IN: %(funcName)s MESSAGE: %(message)s", filemode="w")
logging.info("DATABASE: База данных создана")

def select_n_last_messages(user_id, n_last_messages=1):
    messages = []  # список с сообщениями
    total_spent_tokens = 0  # количество потраченных токенов за всё время общения
    try:
        # подключаемся к базе данных
        print("Получилось")
        with sqlite3.connect('messages.db') as conn:
            cursor = conn.cursor()
            # получаем последние <n_last_messages> сообщения для пользователя
            cursor.execute('''
            SELECT message, role, total_gpt_tokens FROM messages WHERE user_id=? ORDER BY id DESC LIMIT ?''',
                           (user_id, n_last_messages))
            data = cursor.fetchall()
            # проверяем data на наличие хоть какого-то полученного результата запроса
            # и на то, что в результате запроса есть хотя бы одно сообщение - data[0]
            if data and data[0]:
                # формируем список сообщений
                for message in reversed(data):
                    messages.append({'text': message[0], 'role': message[1]})
                    total_spent_tokens = max(total_spent_tokens, message[2])  # находим максимальное количество потраченных токенов
            # если результата нет, так как у нас ещё нет сообщений - возвращаем значения по умолчанию
            return messages, total_spent_tokens
    except Exception as e:
        print('Ошибка')
        logging.error(e)  # если ошибка - записываем её в логи
        return messages, total_spent_tokens



def count_all_limits(user_id, limit_type):
    try:
        # подключаемся к базе данных
        with sqlite3.connect('messages.db') as conn:
            cursor = conn.cursor()
            # считаем лимиты по <limit_type>, которые использовал пользователь
            cursor.execute(f'''SELECT SUM({limit_type}) FROM messages WHERE user_id=?''', (user_id,))
            data = cursor.fetchone()
            # проверяем data на наличие хоть какого-то полученного результата запроса
            # и на то, что в результате запроса мы получили какое-то число в data[0]
            if data and data[0]:
                # если результат есть и data[0] == какому-то числу, то:
                logging.info(f"DATABASE: У user_id={user_id} использовано {data[0]} {limit_type}")
                return data[0]  # возвращаем это число - сумму всех потраченных <limit_type>
            else:
                # результата нет, так как у нас ещё нет записей о потраченных <limit_type>
                return 0  # возвращаем 0
    except Exception as e:
        logging.error(e)  # если ошибка - записываем её в логи
        return 0


@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, 'Привет! Этот бот поможет сгенерировать имя. Для вывода списка доступных команд нажмите /help')


@bot.message_handler(commands=['help'])
def help_user(message):
    bot.send_message(message.chat.id, '/start - перезапуск бота\n/help - помощь\n/generate - начать генерацию')


@bot.message_handler(commands=['debug'])
def debug(message):
    with open('logs.txt', 'rb') as f: 
        bot.send_document(message.chat.id, f) 


@bot.message_handler(commands=['generate'])
def generate_handler(message):
    bot.send_message(message.chat.id, 'Напиши, какое ты хочешь имя')
    bot.register_next_step_handler(message, generate)


def generate(message):
    try:
        # ВАЛИДАЦИЯ: проверяем, есть ли место для ещё одного пользователя (если пользователь новый)
        status_check_users, error_message = check_number_of_users(message.from_user.id)
        if not status_check_users:
            bot.send_message(message.from_user.id, error_message)  # мест нет =(
            return
        # БД: добавляем сообщение пользователя и его роль в базу данных
        add_message(user_id=message.from_user.id, message=message.text, role='user',
					total_gpt_tokens=count_tokens(message.text))
        print(message.text)

        # ВАЛИДАЦИЯ: считаем количество доступных пользователю GPT-токенов
        # получаем последние 4 (COUNT_LAST_MSG) сообщения и количество уже потраченных токенов
        last_messages, total_spent_tokens = select_n_last_messages(message.from_user.id)
        print(last_messages)
        # получаем сумму уже потраченных токенов + токенов в новом сообщении и оставшиеся лимиты пользователя
        total_gpt_tokens, error_message = is_gpt_token_limit(last_messages, total_spent_tokens)
        if error_message:
            # если что-то пошло не так — уведомляем пользователя и прекращаем выполнение функции
            bot.send_message(message.from_user.id, error_message)
            return

        # GPT: отправляем запрос к GPT
        answer_gpt = ask_gpt(message.text)
        # сумма всех потраченных токенов + токены в ответе GPT
        total_gpt_tokens += count_tokens(answer_gpt)

        # БД: добавляем ответ GPT и потраченные токены в базу данных
        add_message(user_id=message.from_user.id, message=answer_gpt, role='assistant',
					total_gpt_tokens=(count_tokens(answer_gpt) + count_tokens(message.text)))

        bot.send_message(message.from_user.id, answer_gpt, reply_to_message_id=message.id)

    except Exception as e:
        logging.error(e)  # если ошибка — записываем её в логи
        bot.send_message(message.from_user.id, "Не получилось ответить. Попробуй написать другое сообщение")

bot.infinity_polling()
