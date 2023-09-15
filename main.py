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



def get_our_position(tender_link):
    participants = []
    player = 0

    driver.get(tender_link)
    html_code = driver.page_source
    soup = BeautifulSoup(html_code, 'html.parser')
    target_div = soup.find('div', {'class': 'table-wrap table-wrap--wide'})
    # print(target_div)
    main_soup = BeautifulSoup(str(target_div), 'html.parser')
    thead = main_soup.find('tr', {'class': 'thead'})
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

    # # tbody = soup.find('tr', {'class': 'tbody'})
    # tbody = soup.find('tbody')
    # # elements = tbody.find_all(attrs={'data-tr-eq': True})
    elements = main_soup.find_all(class_="c1 auction_offer_row_separator position_row")
    our_positions = []
    pos_list = []
    # position_rename = {
    #     'Дата отгрузки': ' <b>├─ Дата отгрузки</b>',
    #     'Место отгрузки: ': '\n <b>├─ Место отгрузки:</b>\n',
    #     'Общее доступное количество данной позиции (кг):': '\n <b>├─ Общее доступное количество (кг):</b>',
    #     'Минимальный объем в заявке (кг):': '\n <b>├─ Минимальный объем в заявке (кг):</b>',
    #     'Базис отгрузки: ': '\n <b>├─ Базис отгрузки:</b>\n',
    # }

    offer_row_separators_position_row = []

    for num, e in enumerate(elements):
        el = BeautifulSoup(str(e), 'html.parser').find_all(class_="multi_winner_offer_cell")
        for n, elem in enumerate(el):
            # print(n, _.text)
            if n == player:
                if elem.text != '—':
                    collapsible_content = e.find(class_="collapsible-content as-hidden")
                    position_data = ''
                    if collapsible_content:
                        # Избавимся от экранирования в ключах для упрощения
                        ordered_keys = [
                            "Дата отгрузки",
                            "Общее доступное количество данной позиции (кг)",
                            "Минимальный объем в заявке (кг)",
                            "Базис отгрузки",
                            "Место отгрузки"
                        ]

                        # Инициализируем словарь для сохранения результатов
                        position_data = {}

                        # Для каждого ключа ищем его начало и конец в строке
                        for i, key in enumerate(ordered_keys):
                            key_with_colon = f"{key}:"
                            start_idx = collapsible_content.text.find(key_with_colon)

                            if start_idx == -1:
                                continue  # если ключ не найден, переходим к следующему

                            start_idx += len(key_with_colon)  # начало значения

                            # ищем начало следующего ключа (или конец строки)
                            if i + 1 < len(ordered_keys):
                                end_idx = collapsible_content.text.find(ordered_keys[i + 1])
                            else:
                                end_idx = len(collapsible_content.text)

                            # извлекаем значение
                            value = collapsible_content.text[start_idx:end_idx].strip()

                            # сохраняем в словаре
                            position_data[key] = value
                        # print(position_data)
                        # parsed_data

                        # print(f"Collapsible Content: {collapsible_content.text}")
                        # position_data = str(collapsible_content.text)
                        # for k, v in position_rename.items():
                        #     position_data = position_data.replace(k, v)

                    else:
                        pass
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
                                          "our_amount":         amount,  # DS: наш объем заявки (кг)
                                          "position_data":      position_data  # DS: наш объем заявки (кг)
                                          })
                    offer_row_separators_position_row.append(num)
    print(our_positions)

    offer_row_separators = []

    elements = soup.find_all(class_='c1 auction_offer_row_separator')

    # print(our_positions)
    for p in our_positions:
        # print(p)
        for num, e in enumerate(elements):

            if f"Итого по лоту №{p['visible_number']} " in e.text:
                fragment_soup = BeautifulSoup(str(e), 'html.parser')
                els = fragment_soup.find_all(class_="c1 auction_offer_row_separator", attrs={"data-tr-eq": True})
                for element in els:
                    data_tr_eq_value = element.get('data-tr-eq')
                    p['score_string'] = data_tr_eq_value
                    offer_row_separators.append(num)
                    # print(f"Значение атрибута data-tr-eq: {data_tr_eq_value}")

                els = fragment_soup.find_all(class_="position_group_multi_winner_offer_cell")
                for i, element in enumerate(els):
                    if i == player:
                        p['position'] = int(str(element.text).split(' место')[0])


    r = get_other_positions(main_soup, offer_row_separators, offer_row_separators_position_row)
    # print(offer_row_separators, offer_row_separators_position_row)
    return our_positions, player
    # print()
    # print(participants)


def get_other_positions(main_soup, offer_row_separators, offer_row_separators_position_row):
    print(offer_row_separators_position_row)
    print(offer_row_separators)
    aggregate = {}
    for n, row in enumerate(offer_row_separators_position_row):
        aggregate[row] = offer_row_separators[n]
    print(aggregate)

    other_amounts = {}
    elements = main_soup.find_all(class_="c1 auction_offer_row_separator position_row")
    for num, e in enumerate(elements):
        for row in offer_row_separators_position_row:
            if num == row:
                el = BeautifulSoup(str(e), 'html.parser').find_all(class_="multi_winner_offer_cell")
                for n, elem in enumerate(el):
                    if elem.text != '—':

                        amount = elem.text.split('Количество килограмм: ')[1]
                        amount = int(amount.split('кг')[0].replace(' ', '').replace('\xa0', ''))

                        # Инициализируем вложенный словарь, если он еще не существует
                        if num not in other_amounts:
                            other_amounts[num] = {}

                        # Добавляем новую пару ключ-значение в вложенный словарь
                        other_amounts[num][n] = amount
    elements = main_soup.find_all(class_='c1 auction_offer_row_separator')
    other_positions = {}
    for num in offer_row_separators:  # перебор только по тем строкам, что указаны в offer_row_separators
        e = elements[num]  # соответствующий элемент из списка elements
        position_cells = {}
        # поиск всех нужных td-элементов внутри e
        all_cells = e.find_all('td')
        for cell_num, cell in enumerate(all_cells):
            cell_classes = cell.get('class', [])
            if "position_group_multi_winner_offer_cell" in cell_classes:
                position_cells[cell_num] = {'text': cell.text.strip(), 'highlighted': 'highlighted' in cell_classes}

        other_positions[num] = position_cells

    print(other_positions)
    print(other_amounts)

@dp.message(Command(commands=['select']))
async def cmd_select(message: types.Message, command: CommandObject):
    if 'b2b-center.ru/market/' in command.args:
        messages_1 = []
        messages_2 = []
        tender_link = command.args
        print(tender_link)
        result = get_our_position(tender_link)
        await bot.send_message(message.from_user.id, f'<b>Позиции по лотам в текущем <a href="{tender_link}">тендере</a>:</b>', parse_mode='HTML')

        for _ in result[0]:
            # print(_['position_data'])
            flag = '🟩'
            # placeholder = ''
            bid_info = ''
            for k, v in _['position_data'].items():
                bid_info += f'<b>├─ {k}:</b> {v}\n'
            placeholder = f'<b>├─ Позиции участников перед нами:</b>\n' \
                          f'<b>├─ [1]</b> ─ 1500 кг.\n' \
                          f'<b>├─ Общая выборка перед нами (включительно):</b>\n' \
                          f'├─ 100000 / {_["position_data"]["Общее доступное количество данной позиции (кг)"]}\n'
            position_string = f"<b> {flag}  Лот №{_['visible_number']}</b>\n" \
                              f"{bid_info}" \
                              f"{placeholder}" \
                              f"<b>├─ Наша цена:</b> {_['our_price']} руб.\n" \
                              f"<b>├─ Наш объем:</b> {_['our_amount']} кг.\n" \
                              f"<b>└─ Наша позиция:</b> №{_['position']}"
            msg = await bot.send_message(message.from_user.id, position_string, parse_mode='HTML')


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