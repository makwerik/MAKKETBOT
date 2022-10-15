import requests
import json
import re
import time
import yaml
import pymysql


class MarketBot:
    """docstring for MarketBot"""

    def __init__(self, bd_connect=None, list_items=None):
        if not bd_connect:
            print('Укажите путь до настроек БД')
        if not list_items:
            print('Укажите путь до списка вещей')
        else:
            with open(bd_connect, 'r', encoding='utf8') as cfg:
                params = yaml.load(cfg, Loader=yaml.Loader)
                self.connect = pymysql.connect(
                    host=params['host'],
                    port=3306,
                    user=params['username'],
                    password=params['password'],
                    database=params['bd_name'],
                    cursorclass=pymysql.cursors.DictCursor
                )
            print('Подключение к базе данных: успешно!')
            with open(list_items, 'r', encoding='utf8') as li:
                li = yaml.load(li, Loader=yaml.Loader)
                self.link_items = li['link_items']
            print('Ссылки на вещи получены!')

    def create_base(self):
        """Создаю курсор для работы и последующей записи информации в БД"""
        with self.connect.cursor() as cursor:
            try:
                create_table = "CREATE TABLE items(id int AUTO_INCREMENT, name varchar(100), link varchar(150), price varchar(100), my_order varchar(100), PRIMARY KEY(id));"
                cursor.execute(create_table)
            except:
                print('Таблица существует!')

    def write_base(self):
        """Функция записи информации в БД"""
        with self.connect.cursor() as cursor:
            # Получение ссылки на вещь\ Получение ордера и +2 к его стоимости\ Запись в таблицу
            for link in self.link_items:
                link_response = re.search(r'\d+\D\d+', link.replace('-', '_'))
                get_name = requests.get(
                    f'https://market.csgo.com/api/ItemInfo/{link_response[0]}/ru/?key=Va56rV8ivaR110Ut202XGk6LeaRkSeD').json().get(
                    'market_hash_name')
                get_order = requests.get(
                    f'https://market.csgo.com/api/BestBuyOffer/{link_response[0]}/?key=Va56rV8ivaR110Ut202XGk6LeaRkSeD').json().get(
                    'best_offer')
                get_order = str(int(get_order) + 2)
                get_price = requests.get(
                    f'https://market.csgo.com/api/BestSellOffer/{link_response[0]}/?key=Va56rV8ivaR110Ut202XGk6LeaRkSeD').json().get(
                    'best_offer')
                values = (get_name, link, get_price, get_order)
                insert = "INSERT INTO items(name,link,price,my_order) VALUES(%s,%s,%s,%s)"
                cursor.execute(insert, values)
                self.connect.commit()
        print('Данные успешно записаны!')

    def delete_base(self):
        """Удаление БД"""
        with self.connect.cursor() as cursor:
            drop_base = "DROP TABLE items;"
            cursor.execute(drop_base)

    def sent_order(self):
        """Выставляю ордер по БД"""
        with self.connect.cursor() as cursor:
            get_info_base = "SELECT name,link,my_order FROM items"
            cursor.execute(get_info_base)
            for info_base in cursor.fetchall():
                name_base = info_base.get('name')
                link_base = re.search(r'\d+\D\d+', info_base.get('link').replace('-', '/'))[0]
                order_base = info_base.get('my_order')
                buy_items = requests.get(
                    f'https://market.csgo.com/api/ProcessOrder/{link_base}/{order_base}//?key=Va56rV8ivaR110Ut202XGk6LeaRkSeD')
                print(f"Название: {name_base} --- Ордер: {order_base} --- Ссылка: {info_base.get('link')}")
                print(link_base)
        print('Ордера выставлены!')

    def check_order(self):
        """Проверка ордеров и их последующее изменение, если выгодно"""
        with self.connect.cursor() as cursor:
            check_info_base = "SELECT id,name,link,my_order FROM items"
            cursor.execute(check_info_base)
            for check_base in cursor.fetchall():
                id_check_base = int(check_base.get('id'))
                name_check_base = check_base.get('name')
                link_check_base = re.search(r'\d+\D\d+', check_base.get('link').replace('-', '_'))[0]
                order_check_base = check_base.get('my_order')
                # Проверяю ордер маркета
                try:
                    get_best_order_market = requests.get(
                        f'https://market.csgo.com/api/BuyOffers/{link_check_base}/?key=Va56rV8ivaR110Ut202XGk6LeaRkSeD').json().get(
                        'best_offer')
                    # Если ордера отличаются,то меняю
                    if int(order_check_base) != int(get_best_order_market):
                        new_order_base = str(int(get_best_order_market) + 1)
                        update_my_order_base = "UPDATE items SET my_order = %s WHERE id = %s"
                        cursor.execute(update_my_order_base, (new_order_base, id_check_base))
                        self.connect.commit()
                        return 'sent'
                except:
                    return 'Eror'

    def delete_orders(self):
        """Удаление всех ордеров"""
        delet_my_orders = requests.get('https://market.csgo.com/api/DeleteOrders/?key=Va56rV8ivaR110Ut202XGk6LeaRkSeD')


b = MarketBot(r'data/cfg.yaml', r'data/items.yaml')
while True:
    if b.check_order() == 'sent':
        b.sent_order()

