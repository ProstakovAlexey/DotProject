# coding=utf8
__author__ = 'Prostakov Alexey'
"""
Описание
**********************
В этом файле собраны функции для работы с конфигурационным файлом.
"""
import os
import configparser


def readConfig(file="config.ini"):
    '''
    Разбирает конфигурационный файл
    :param file: имя файла конфигурации
    :return: словарь, первый ключ - имя секции, значение - словарь с константами
    и кол-во ошибок
    '''
    DB = dict()
    users = list()
    err = 0
    if os.access(file, os.F_OK):
        # выполняется если найден конфигурационный файл
        config_str = open(file, encoding='utf-8', mode='r').read()
        # удалить признак кодировки
        config_str = config_str.replace(u'\ufeff', '')
        Config = configparser.ConfigParser()
        Config.read_string(config_str)
        sections = Config.sections()
        for section in sections:
            i = Config[section]
            if section == 'DB':
                DB['name'] = i.get('name', fallback='')
                DB['adr'] = i.get('address', fallback='')
                DB['port'] = i.get('port', fallback='')
                DB['user'] = i.get('user', fallback='sa')
                DB['pwd'] = i.get('password', fallback='111')
            elif section.count('user'):
                # Каждого пользователя храним в словаре
                # находим его атрибуты и добовляю в список пользователей
                user = dict()
                user['id'] = i.get('id', fallback= "")
                user['email'] = i.get('email', fallback= "")
                user['name'] = i.get('name', fallback="Не указано")
                user['correct1'] = i.get('Рассматривается', fallback=0)
                users.append(user)
    else:
        print("Ошибка! Не найден конфигурационный файл")
        err = 1
    return DB, users, err


def configValidator(DB, users):
    """
    Проверяет заполнение обязательных полей в настройках
    :param DB:  словарь для БД
    :param users: список пользователей
    :return: сообщение об ошибках
    """
    errMess = ""
    if DB['name'] == '':
        errMess +="Не заполнено наименование БД. "
    if DB['adr'] == '':
        errMess += "Не заполнен адрес сервера БД."
    if DB['port'] == '':
        errMess += 'Не заполнен порт сервера БД'
    if DB['user'] == '':
        errMess += 'Не заполнено имя пользователя для подключения к БД.'

    if users :
        for user in users:
            if user['id'] == '':
                errMess += 'Не заполен ИД пользователя дотпроджекта'
    else:
        errMess += 'Нет ни одного пользователя для допроджекта'
    return errMess