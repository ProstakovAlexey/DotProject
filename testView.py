#!/usr/bin/python3.4
# -*- coding: utf-8 -*-
import config
import pypyodbc
import datetime

__author__ = 'Prostakov Alexey'
"""
1. Находит в ДПР все мои наборы тестов на текущую дату.
2. Находит в ДПР все задания на испраление ошибок (15), к которым приделаны есть мои тесты.
3. Находит в ДПР все задания на испраление ошибок, к которым приделаны есть мои тесты, не имеющие статуса выполнено или отменено (3 и 5).
4. Складывает данные в файл: дата  п.1  п.2  п.3
"""

def getD1(cur):
    """ Находит в ДПР все мои наборы тестов на текущую дату
    :param cur: курсор
    :return: кол-во таких тестов
    """
    cur.execute('SELECT count(id) FROM Tests where userID=2')
    return cur.fetchone()[0]


def getD2(cur):
    """Находит в ДПР все задания на испраление ошибок, к которым приделаны мои тесты
    :param cur: курсор
    :return: кол-во таких тестов
    """
    cur.execute('SELECT count(id) FROM Tasks where TEST in (SELECT id FROM Tests where userID=2)')
    return cur.fetchone()[0]


def getD3(cur):
    """Находит в ДПР все задания на испраление ошибок, к которым приделаны есть мои тесты, не имеющие статуса
    выполнено или отменено (3 и 5)
    :param cur: курсор
    :return: кол-во таких тестов
    """
    cur.execute('SELECT count(id) FROM Tasks where TEST in (SELECT id FROM Tests where userID=2) and not (StatusId in (3,5))')
    return cur.fetchone()[0]


if __name__ == '__main__':
    # Выполняется если файл запускается как программа
    # читаю конфигурационный файл
    DB, users, work, err = config.readConfig()
    if err:
        exit(1)
    # пробуем соединится с БД
    try:
        con = pypyodbc.connect(
                'DRIVER=FreeTDS; SERVER=%s; PORT=%s; DATABASE=%s; UID=%s; PWD=%s; TDS_Version=8.0; ClientCharset=UTF8;'
                % (DB['adr'], DB['port'], DB['name'], DB['user'], DB['pwd']))
        cur = con.cursor()
    except:
        print("Возникла ошибка при соединении с БД")
        exit(1)
    # Начальные настройки
    fileName = 'testView.txt'

    # Получаю текущую дату
    d0 = datetime.datetime.today().strftime('%Y-%m-%d')
    # Получаю данные по п.1
    d1 = getD1(cur)
    # Получаю данные по п.2
    d2 = getD2(cur)
    # Получаю данные по п.3
    d3 = getD3(cur)

    # Запись их в файл
    with open(fileName, mode='a', encoding='utf-8') as fp:
        print(d0, d1, d2, d3, file=fp)

    # Закрываю соединение с БД
    con.close()
    exit(0)