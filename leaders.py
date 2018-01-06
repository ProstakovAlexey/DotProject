# -*- coding: utf-8 -*-
import config
import platform
import datetime
import argparse
from slacker import Slacker
import logging
import pyodbc


def obr_analiz(user_id, start_date, period_for_report, connection):
    """
    Из БД извлекает сведения по обращениям, анализирует их и выдает кол-во обращений за указанный период
    по 3-м видам: консультации, доработки, ошибки
    :param user_id: номер пользователя
    :param start_date: начало периода (включительно)
    :param period_for_report: окончание периода (включительно)
    :param connection: соединение с БД
    :return: список (консультации, доработки, ошибки)
    """
    # По умолчанию возьмем за неделю
    end_date = start_date - datetime.timedelta(days=7)
    format_str = '%Y-%m-%dT23:59:59'
    sql_string = "SELECT TargetObrTypeId FROM Obr where USERID=%s and DatObr BETWEEN '%s' AND '%s'" % \
                 (user_id, end_date.strftime(format_str), start_date.strftime(format_str))
    if period_for_report == 'day':
        sql_string = "SELECT TargetObrTypeId FROM Obr where USERID=%s and year(DatObr)=%s and MONTH(DatObr)=%s" \
                     "and DAY(DatObr)=%s" % (user_id, start_date.year, start_date.month, start_date.day)
    elif period_for_report == 'month':
        sql_string = "SELECT TargetObrTypeId FROM Obr where USERID=%s and year(DatObr)=%s and MONTH(DatObr)=%s" % \
                     (user_id, start_date.year, start_date.month)
    cur = connection.cursor()
    cur.execute(sql_string)
    # Инициализация консультация, новое, ошибки
    consultation = 0
    new_work = 0
    fix_error = 0

    '''В курсоре весь список обращений за нужный период. Виды обращения в TargetObrTypeId:
    1 - консультация
    2 - доработка
    3 - ошибка
    '''
    for obr in cur.fetchall():
        if obr[0] == 1:
            consultation += 1
        elif obr[0] == 2:
            new_work += 1
        elif obr[0] == 3:
            fix_error += 1
    return consultation, new_work, fix_error


def get_сonnect(db_info):
    """ Соединяется с БД, возвращает коннектион. Если не получается, то завершает работу.
    :param db_info: словарь с параметрами для соединения
    :return: коннект и сообщение об ошибке (None если все хорошо)
    """
    err_string = None
    con_result = None
    con_string = None
    # Определяет, на какой ОС запущен, т.к. я запускаю и на windows
    os = platform.system()
    try:
        if os == 'Windows':
            # Для windows 2003 тут нужно указать другую версию клиента
            con_string = 'DRIVER={SQL Server Native Client 11.0}; SERVER=%s; DATABASE=%s; UID=sa; PWD=%s' \
                   % (db_info['adr'], db_info['name'], db_info['pwd'])
            con_result = pyodbc.connect(con_string)
        elif os == 'Linux':
            con_string = "DRIVER={ODBC Driver 13 for SQL Server}; SERVER=%s,%s; DATABASE=%s; UID=sa; PWD=%s;" %\
                      (db_info['adr'], db_info['port'], db_info['name'], db_info['pwd'])
            con_result = pyodbc.connect(con_string)
        else:
            err_string = 'Запущен на не известной ОС. Работает только с Linux и Windows.'
    except pyodbc.InterfaceError as err:
        err_string = "Возникла ошибка при соединении с БД ТИ %s, строка соединения %s" % (err, con_string)
    return con_result, err_string


def find_max_obr(m):
    """
    Находит 5 пользователь у кого больше всего обращений
    :param m: словарь с инф. по массовой операции
    :return: список id, по убыванию обращений.
    """
    # Список уже найденных
    z = list()
    n = 0
    while n <= 5:
        # Это нужно, если у всех 0 обращений, чтобы чей-то id попал в статистику
        max_obr = -1
        max_name = 0
        for key in m.keys():
            if (m[key][0] > max_obr) and not (key in z):
                max_name = key
                max_obr = m[key][0]
        n += 1
        z.append(max_name)
    return z


if __name__ == '__main__':
    # Будет создавать новый лог файл каждый день
    log_file_name = r'logs/' + datetime.datetime.today().strftime(r'%Y-%m-%d') + '_Лидеры.log'
    logging.basicConfig(filename=log_file_name, filemode='a', level=logging.DEBUG,
                        format='%(asctime)s %(levelname)s: %(message)s')
    # Получаем параметры коммандной строки, т.к. может считать за день, неделю, месяц
    parser = argparse.ArgumentParser(
        description="Получает в качестве параметра за какой период считать. "
                    "Бежит по конф. файлу и проводит подсчет статистики по обращения для тех пользователей,"
                    " у кого стоит флаг stat=1. В статистике обращения разбивает на группы: "
                    "консультации, доработки, ошибки. Результат отправляет в slack.")
    # Может принять следующие аргументы
    parser.add_argument('-p', metavar='p', type=str, nargs=1, help='Период. Принимает значения: day, week, month')
    args = parser.parse_args()
    logging.info('Программа запущена c аргументами: %s' % args)
    period = 'week'
    if args.p is None:
        logging.critical('Программе надо передать период. Выполните с ключем --help для получения помощи.')
        exit(1)
    if not (args.p[0] in ('day', 'week', 'month')):
        logging.critical('Получил неизвестный период - %s, проверьте аргументы программы.' % args.p[0])
        exit(1)
    else:
        period = args.p[0]
    # Прочитать токен  для робота
    with open('token.txt', mode='r', encoding='utf-8') as fp:
        testToken = fp.read()
    slack = Slacker(testToken)
    logging.debug('Соединился со Slack')
    # Читаю конфигурационный файл
    DB, users, work, imap, err_message = config.readConfig()
    if err_message:
        logging.critical(err_message)
        exit(1)
    # Соединение с БД
    con, err_message = get_сonnect(DB)
    # При соединении возникла ошибка, закончим работу
    if err_message:
        logging.critical(err_message)
        exit(1)
    logging.debug('Успешно соединились с БД')
    users_stat = dict()
    for user in users:
        сons, dorab, err = obr_analiz(
            user['id'], datetime.datetime.today() - datetime.timedelta(days=1), period, con)
        total = сons + dorab + err
        users_stat[user['id']] = (total, сons, dorab, err)
    # Находим 5 лидеров
    leader_peoples = find_max_obr(users_stat)
    logging.debug('Найдены 5 лидеров по обращения: %s' % leader_peoples)
    for user in users:
        # Хочет ли пользователь получать статистику?
        if user['stat']:
            logging.debug('Обрабатываю пользователя %s' % user['name'])
            msg = ''
            total, сons, dorab, err = users_stat[user['id']]
            # Выше я уже проверял что период корректный, поэтому сейчас по нему сразу запрашиваю.
            # Предполагаю, что буду спрашивать по cron на следующий день, поэтому -1
            if period == 'week':
                msg = 'За прошедшую неделю всего было обращений - %s. Из них консультации %s, ' \
                      'исправление ошибок %s, доработки %s.' % (total, сons, err, dorab)
            elif period == 'day':
                msg = 'За прошедший день всего было обращений - %s. Из них консультации %s, ' \
                      'исправление ошибок %s, доработки %s.' % (total, сons, err, dorab)
            elif period == 'month':
                msg = 'За прошедший месяц всего было обращений - %s. Из них консультации %s, ' \
                      'исправление ошибок %s, доработки %s.' % (total, сons, err, dorab)
            msg += r' У лучшего социтовца %s обращений.' % users_stat[leader_peoples[0]][0]
            if user['id'] in leader_peoples:
                msg += ' Ты в пятерке лидеров, можно расслабиться и отдохнуть.'
            else:
                msg += ' Ты не в пятерке лидеров, у 5-го %s обращений, поднажми!' % users_stat[leader_peoples[4]][0]
            logging.debug('Сообщение: %s' % msg)
            if user['slack']:
                # Указан шлак, шлем сюда
                slack.chat.post_message('@' + user['slack'], msg, as_user=True)
                logging.debug('Успешно отправлено оповещение в slack')

    # Закрыть соединение
    con.close()
    logging.info('Программа работы закончила')
    exit(0)
