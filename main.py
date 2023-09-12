from selenium.webdriver.common.by import By
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import asyncio
from aiogram.filters import Command, CommandObject, Text
from aiogram import Bot, Dispatcher, types, Router, F
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import \
    ReplyKeyboardMarkup, ReplyKeyboardBuilder, InlineKeyboardBuilder, \
    InlineKeyboardMarkup, InlineKeyboardButton, KeyboardButton
from aiogram.types import FSInputFile
import os
import logging
from logging import getLogger
from logging.handlers import RotatingFileHandler
import traceback


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
log_filename = 'b2b_project.log'
log_max_size = 10 * 1024 * 1024  # DS: 10 МБ размер файла логов
log_backup_count = 10  # DS: 10 файлов бекапа
log_handler = RotatingFileHandler(log_filename, maxBytes=log_max_size, backupCount=log_backup_count)
log_handler.setLevel(logging.INFO)
logging.getLogger('aiogram').setLevel(logging.WARNING)  # DS: ограничение технических сообщений от aiogram
formatter = logging.Formatter('%(asctime)s <%(levelname)s, %(traceback)s %(message)s')
log_handler.setFormatter(formatter)
logger.addHandler(log_handler)


project_dir = os.getcwd()


def log_message(log_type, user_id, message, traceback_):
    traceback_ = str(traceback_).replace(project_dir, '').replace(r"<FrameSummary file ", "")
    if log_type == 'info':
        logger.info(message,
                    extra={'user_id': user_id, 'traceback': traceback_})
    elif log_type == 'warning':
        logger.warning(message,
                       extra={'user_id': user_id, 'traceback': traceback_})
    elif log_type == 'error':
        logger.error(message,
                     extra={'user_id': user_id, 'traceback': traceback_})


users = []
token = ''
chrome_profile_path = ''

with open("config.txt", "r") as config_file:
    lines = config_file.readlines()
for line in lines:
    if "TELEGRAM_BOT_TOKEN" in line:
        token = line.split("=")[1].strip().strip('"')

    elif "USER_TELEGRAM_ID" in line:
        users_string = line.split("=")[1].strip().strip('"')
        for u in users_string.split(','):
            users.append(u.strip())

    elif "CHROME_PROFILE_PATH" in line:
        chrome_profile_path = line.split("=")[1].strip().strip('"')

storage = MemoryStorage()
bot = Bot(token=token, parse_mode="HTML")
dp = Dispatcher(storage=storage)

@dp.message(Command(commands=['start']))
async def cmd_start(message: types.Message):
    await bot.send_message(message.from_user.id, f"Ваш telegram ID: {message.from_user.id}")
    log_message('info', message.from_user.id, 'Отправил пользователю телеграм айди', traceback.extract_stack()[-1])



options = Options()
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)
options.add_argument("--log-level=3")
options.add_argument('--start-maximized')
options.add_argument("user-data-dir=" + chrome_profile_path)
options.add_argument("--headless")
driver = webdriver.Chrome(options=options)


@dp.message(Command(commands=['select']))
async def cmd_select(message: types.Message, command: CommandObject):
    tender_link = command.args
    print(tender_link)
    await bot.send_message(message.from_user.id, f'Приступаю к обработке тендера по ссылке:\n{tender_link}')


@dp.message(Command(commands=['info']))
async def cmd_info(message: types.Message):
    await bot.send_message(message.from_user.id, f"<b>Бот работает следующим образом:</b>\n\n"
                                                 f"По команде <b>'/select + ссылка на тендер'</b> бот переходит на указанную"
                                                 f" страницу и проверяет является ли ваш аккаунт участником процедуры,"
                                                 f" и если да, то узнает ваш номер (в плашке вверху страницы), после "
                                                 f"чего проверяет все лоты тендера и находит лоты в которых имеется "
                                                 f"ставка участника, соответствующая вашему номеру внутри процедуры. "
                                                 f"После того как проверены все лоты - запоминаются только те, в "
                                                 f"которых вы участвуете и анализирует изменение  позиций и объемов "
                                                 f"закупок каждого из игроков, соотнося их с общим объемом лота.\n\n"
                                                 f"<b>Пример команды на проверку процедуры:</b>\n"
                                                 f"/select https://www.b2b-center.ru/market/view.html?id=3424166&action=offers")
    log_message('info', message.from_user.id, 'Отправил пользователю телеграм айди', traceback.extract_stack()[-1])

async def on_startapp():
    try:
        print("Bot is online now")
        log_message('info', 'admin', 'Бот запущен', traceback.extract_stack()[-1])
        await dp.start_polling(bot)
    except Exception as e:
        print(e)
        log_message('info', 'admin', e, traceback.extract_stack()[-1])
    finally:
        await bot.session.close()
        print("Bot is offline now")



if __name__ == '__main__':
    asyncio.run(on_startapp())