# -*- coding: utf-8 -*-
import config
import pypyodbc
import platform
import datetime
import argparse
from slacker import Slacker


def obr_analiz(user_id, start_date, period, con):
    """
    Из БД извлекает сведения по обращениям, анализирует их и выдает кол-во обращений за указанный период
    по 3-м видам: консультации, доработки, ошибки
    :param user_id: номер пользователя
    :param start_date: начало периода (включительно)
    :param period: окончание периода (включительно)
    :param con: соединение с БД
    :return: список (консультации, доработки, ошибки)
    """
    if period == 'day':
        sql_string = "SELECT TargetObrTypeId FROM Obr where USERID=%s and year(DatObr)=%s and MONTH(DatObr)=%s" \
                     "and DAY(DatObr)=%s" % (user_id, start_date.year, start_date.month, start_date.day)
    elif period == 'week':
        end_date = start_date + datetime.timedelta(days=7)
        format_str = '%Y-%m-%dT%H:%M:%S'
        sql_string = "SELECT TargetObrTypeId FROM Obr where USERID=%s and DatObr BETWEEN '%s' AND '%s'" % \
                     (user_id, start_date.strftime(format_str), end_date.strftime(format_str))
    elif period == 'month':
        sql_string = "SELECT TargetObrTypeId FROM Obr where USERID=%s and year(DatObr)=%s and MONTH(DatObr)=%s" % \
                     (user_id, start_date.year, start_date.month)
    cur = con.cursor()
    #print(sql_string)
    cur.execute(sql_string)
    # Инициализация
    kons = 0
    dorab = 0
    err = 0
    '''В курсоре весь список обращений за нужный период. Виды обращения в TargetObrTypeId:
    1 - консультация
    2 - доработка
    3 - ошибка
    '''
    for obr in cur.fetchall():
        if obr[0] == 1:
            kons += 1
        elif obr[0] == 2:
            dorab += 1
        elif obr[0] == 3:
            err += 1
    return kons, dorab, err


def getConnection (DB):
    """ Соединяется с БД, возвращает коннектион. Если не получается, то завершает работу.
    :param DB: словарь с параметрами для соединения
    :return: коннект
    """
    # определяет, на какой ОС запущен
    os = platform.system()
    if os == 'Linux':
        conS = "DRIVER=FreeTDS; SERVER=%s; PORT=%s; DATABASE=%s; UID=sa; PWD=%s; TDS_Version=8.0; ClientCharset=UTF8; autocommit=True" \
               % (DB['adr'], DB['port'], DB['name'], DB['pwd'])
    elif os == 'Windows':
        # на windows 2003 тут нужно указать другую версию клиента
        conS = 'DRIVER={SQL Server Native Client 11.0}; SERVER=%s; DATABASE=%s; UID=sa; PWD=%s' \
               % (DB['adr'], DB['name'], DB['pwd'])
    else:
        print('Запущен на не известной ОС. Работает только с Linux и Windows.')
        exit(1)
    try:
        # пробую соединится
        con = pypyodbc.connect(conS)
    except:
        print("Возникла ошибка при соединении с БД ТИ, строка соединения %s" % conS)
        exit(1)
    return con


if __name__ == '__main__':
    """Консольная программа, получает в качестве параметра за какой период считать. Потом бежит по конф. файлу
    и проводит подсчет статистики по обращения для тех пользователей, у кого стоит флаг stat. В статистике обращения
    разбивает на группы: консультации, доработки, ошибки. Результат отправляет в slack."""
    # Получаем параметры коммандной строки
    parser = argparse.ArgumentParser(description="""получает в качестве параметра за какой период считать.
    Потом бежит по конф. файлу и проводит подсчет статистики по обращения для тех пользователей, у кого стоит флаг stat.
    В статистике обращения разбивает на группы: консультации, доработки, ошибки. Результат отправляет в slack.""")
    # Может принято следующие аргументы
    parser.add_argument('-p', metavar='p', type=str, nargs=1, help='Период. Принимает значения: day, week, month')
    args = parser.parse_args()
    if args.p is None:
        print('Программе надо передать аргумент -p (период)')
        #args.p = ['month']
        exit(1)
    args.p = args.p[0]
    if not (args.p in ('day', 'week', 'month')):
        print('Получил неизвестный период=%s, проверьте аргументы программы.' % args.p)
        exit(1)
    # Прочитать токен  для робота
    with open('token.txt', mode='r', encoding='utf-8') as fp:
        testToken = fp.read()
    slack = Slacker(testToken)
    # Читаю конфигурационный файл
    DB, users, work, err = config.readConfig()
    if err:
        exit(1)
    # Соединение с БД
    con = getConnection(DB)
    for user in users:
        # Хочет ли пользователь получать статистику?
        if user['stat']:
            msg = ''
            # Выше я уже проверял что период корректный, поэтому сейчас по нему сразу запрашиваю.
            # Предполагаю, что буду спрашивать по cron на следующий день, поэтому -1
            kons, dorab, err = obr_analiz(user['id'],
                                          datetime.datetime.today() - datetime.timedelta(days=1), args.p, con)
            total = kons + dorab + err
            if args.p == 'week':
                msg = 'За прошедшую неделю всего было обращений - %s. Из них консультации %s, исправление ошибок %s, ' \
                      'доработки %s.'% (total, kons, err, dorab)
            elif args.p == 'day':
                msg = 'За прошедший день всего было обращений - %s. Из них консультации %s, исправление ошибок %s, ' \
                      'доработки %s.' % (total, kons, err, dorab)
            elif args.p == 'month':
                msg = 'За прошедший месяц всего было обращений - %s. Из них консультации %s, исправление ошибок ' \
                      '%s, доработки %s.' % (total, kons, err, dorab)
            if user['slack']:
                # Указан шлак, шлем сюда
                slack.chat.post_message('@' + user['slack'], msg, as_user=True)
    # Закрыть соединение
    con.close()
