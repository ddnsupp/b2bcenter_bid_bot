from selenium.webdriver.common.by import By
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
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
from bs4 import BeautifulSoup
import requests
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
personal = ''

with open("config.txt", "r", encoding="utf-8") as config_file:
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

    elif "PERSONAL" in line:
        personal = line.split("=")[1].strip().strip('"')

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


class Participant:
    def __init__(self, name, volume=None, rank=None, cell=None):
        self.name = name  # DS: имя участника торгов
        self.volume = volume  # DS: объем закупки
        self.rank = rank  # DS: текущее положение в рейтинге закупки
        self.cell = cell  # DS: статичный номер ячейки в таблице участников

    def __str__(self):
        return f"Name: {self.name}, Volume: {self.volume}, Rank: {self.rank}, Cell: {self.cell}"

    def update_volume(self, volume):
        self.volume = volume

    def update_rank(self, rank):
        self.rank = rank


participants = []
def get_players(tender_link):
    player = 0

    driver.get(tender_link)
    html_code = driver.page_source
    soup = BeautifulSoup(html_code, 'html.parser')
    target_div = soup.find('div', {'class': 'table-wrap table-wrap--wide'})
    # print(target_div)
    soup = BeautifulSoup(str(target_div), 'html.parser')
    thead = soup.find('tr', {'class': 'thead'})
    # print(thead)
    elements = thead.find_all(class_='company_and_user_info')
    for i, element in enumerate(elements):
        name = element.text.strip()  # Получение имени участника из текста элемента
        cell = i
        if personal in name:
            player = i
        f = next((p for p in participants if p.name == name), None)
        if not f:
            participant = Participant(name=name, cell=cell)  # Создание нового объекта Participant
            participants.append(participant)  # Добавление объекта в список

    print([str(participant) for participant in participants])
    print(participants[player])

    # tbody = soup.find('tr', {'class': 'tbody'})
    tbody = soup.find('tbody')
    # elements = tbody.find_all(attrs={'data-tr-eq': True})
    elements = soup.find_all(class_="c1 auction_offer_row_separator position_row")
    our_positions = []
    for num, e in enumerate(elements):
        el = BeautifulSoup(str(e), 'html.parser').find_all(class_="multi_winner_offer_cell")
        for n, elem in enumerate(el):
            # print(n, _.text)
            if n == player:
                if elem.text != '—':
                    price = elem.text.split('Ранг недоступен в данном типе процедуры')[1]
                    price = float(price.split('руб.')[0].replace(' ', '').replace(',', '.').replace('\xa0', ''))
                    amount = elem.text.split('Количество килограмм: ')[1]
                    amount = int(amount.split('кг')[0].replace(' ', '').replace('\xa0', ''))
                    pos = elem.find_parent(class_="c1 auction_offer_row_separator position_row").find(
                        class_="multi_winner_position_cell").get('position_group_id', 'N/A')
                    # print(f'Вн. номер строки {num}, видимый номер позиции {pos}, номер нашей колонки {n}, наша ставка {price} руб., наш объем {amount} кг.')
                    our_positions.append({"internal_number":    num,    # DS: внутренний номер лота (строки)
                                          "visible_number":     pos,    # DS: отображаемый номер лота (строки)
                                          "our_column":         n,      # DS: номер нашей колонки
                                          "our_price":          price,  # DS: наша цена заявки за единицу (руб)
                                          "our_amount":         amount  # DS: наш объем заявки (кг)
                                          })
    elements = soup.find_all(class_='c1 auction_offer_row_separator')
    # print(our_positions)
    for p in our_positions:
        print(p)
        for num, e in enumerate(elements):
            if e.has_attr("data-colspan-text") and f"Итого по лоту №{p['visible_number']} " in e.text:
                print(e)
                parent_element = e.find_parent(attrs={"data-tr-eq": True})
                if parent_element:
                    data_tr_eq_value = parent_element.get('data-tr-eq')
                    print(data_tr_eq_value.text)
            # el = BeautifulSoup(str(e), 'html.parser').find_all(class_="multi_winner_offer_cell")




@dp.message(Command(commands=['select']))
async def cmd_select(message: types.Message, command: CommandObject):
    if 'b2b-center.ru/market/' in command.args:
        tender_link = command.args
        print(tender_link)
        await bot.send_message(message.from_user.id, f'Приступаю к обработке тендера по ссылке:\n{tender_link}')
        get_players(tender_link)



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