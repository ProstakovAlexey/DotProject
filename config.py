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
    :return: словари и кол-во ошибок
    '''
    DB = dict()
    work = dict()
    users = list()
    imap = dict()
    err = None
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
                user['jabber'] = i.get('jabber', fallback="")
                user['slack'] = i.get('slack', fallback="")
                user['stat'] = i.get('stat', fallback=0)
                user['imap'] = i.get('imap', fallback="")
                user['new_obr'] = i.get('new_obr', fallback=0)
                users.append(user)
            elif section == 'work':
                work['noActiveObr'] = i.get('noActiveObr', fallback="5")
            elif section == 'imap':
                imap['host'] = i.get('host', fallback="127.0.0.1")
                imap['user'] = i.get('user', fallback="socit")
                imap['password'] = i.get('password', fallback="111")
                imap['days'] = int(i.get('days', fallback="3"))

    else:
        err = "Ошибка! Не найден конфигурационный файл"
    return DB, users, work, imap, err


def configValidator(DB, users, work):
    """
    Проверяет заполнение обязательных полей в настройках
    :param DB:  настроек для БД
    :param users: настроек пользователей
    :param work: словарь настроек
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

    if work['noActiveObr'].isdigit() :
        work['noActiveObr'] = int(work['noActiveObr'])
        if work['noActiveObr'] <= 0 :
            errMess += 'Кол-во дней неактивности по обращениям должно быть больше 0 дней.'
    else:
        errMess += 'Кол-во дней неактивности должно быть цифрой'

    if users :
        for user in users:
            if user['id'] == '':
                errMess += 'Не заполен ИД пользователя дотпроджекта'
    else:
        errMess += 'Нет ни одного пользователя для допроджекта'
    return errMess


def read_proj_info(file_name):
    """
    Читает конфигурационный файл с инф. по проекту
    :param file_name: имя файла
    :return: словарь и сообщение об ошибке
    """
    proj = {'project_id': None, 'reg_id': 0}
    err_msg = ""
    if os.access(file_name, os.F_OK):
        # выполняется если найден конфигурационный файл
        config_str = open(file_name, encoding='utf-8', mode='r').read()
        # удалить признак кодировки
        config_str = config_str.replace(u'\ufeff', '')
        Config = configparser.ConfigParser()
        Config.read_string(config_str)
        sections = Config.sections()
        for section in sections:
            i = Config[section]
            if section == 'PROJECT':
                proj['reg_id'] = int(i.get('reg_id', fallback=0))
                proj['project_id'] = int(i.get('project_id', fallback=0))
                proj['obr_id'] = int(i.get('obr_id', fallback=0))
        # Проверка на заполненность
        for key in proj.keys():
            if proj[key] == 0 and key != 'obr_id':
                err_msg += 'Свойство проекта {0} не может быть пустым. '.format(key)
    else:
        err_msg = 'Конфигурационный файл {0} не найден'.format(file_name)
    return proj, err_msg
