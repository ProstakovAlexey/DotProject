# coding=utf8
__author__ = 'Prostakov Alexey'
"""
Проводит анализ
"""
# библиотека для работы с БД
import pypyodbc
import config
import subprocess
import datetime
from slacker import Slacker


def jobList(cur, obr):
    """
    Получает список заданий по обращениям
    :param cur: соединение к БД
    :param obr: номер обращения
    :return: список заданий
    """
    cur.execute('SELECT TaskId FROM Task#Obr WHERE ObrId=?', (obr,))
    jobs = list()
    for job in cur.fetchall():
        jobs.append(job[0])
    return jobs


def obrJobComplete(cur, user):
    """
    Ищет все обращения пользователя со статусом задания выданы,
    у которых все задания закрыты выполенны или отменены.
    :param cur: курсор к БД
    :param user: id специалиста
    :return: список обращений
    """
    msg = ""
    # получаем список обращений пользователя со статусом задания выданы
    cur.execute('SELECT id FROM Obr WHERE UserId = ? and StatusObrId = ?', (user, 6))
    complete = list()
    obr_with_error = list()
    for res in cur.fetchall():
        obr = res[0]
        # находим все задания к этому обращению, у которых статус не равен выполнено или отменено
        jobs = jobList(cur, obr)
        if jobs:
            # по обращению есть задания
            allJob = ''
            for job in jobs:
                allJob += ',' + str(job)
            allJob = allJob[1:]
            # ищем для обращения все задания, которые не выполнены или не отменены
            sql = 'SELECT id FROM Tasks WHERE id in (%s) and StatusId!=3 and StatusId!=5' % allJob
            cur.execute(sql)
            res = cur.fetchone()
            if res == None:
                # не найдены не выполненные задания
                complete.append(str(obr))
        else:
            # Выдает всегда только одно обращение
            obr_with_error.append(str(obr))
    if obr_with_error:          
            msg = 'Ошибка в обращении(ях): %s. Установлен статус задания выданы, а ни одного задания нет.\n' % ';'.join(obr_with_error)
    return complete, msg


def obrValid1(cur, user):
    """
    Находит обращения, по которым уже идет работа, а они висят в статусе новое или принято.
    Меняет им статус на Рассматривается
    :param cur: курсор к БД
    :param user: специалист
    :return: список номеров исправленных обращений
    """
    correctList = list()
    # получаем список обращений пользователя со статусом новое и принято
    cur.execute('SELECT id FROM Obr WHERE UserId = ? and StatusObrId in (1, 4)', (user,))
    obrList = cur.fetchall()
    for i in obrList:
        # получаем номер обращения
        obr = i[0]
        # получаем список пользователей написавших комментарий к этому обращению, у которых тип=1 (социнформтех)
        cur.execute("""select count(id) from Users where id in
        (SELECT DISTINCT userId FROM ObrComment where ObrId = ?) and Users.UserTypeId=1""", (obr,))
        # есть хотя бы один пользователь
        if cur.fetchone()[0] > 0:
            correctList.append(str(obr))
            cur.execute('update Obr set StatusObrId = 3 where Id = ?', (obr,))
    return correctList


def obrValid2(cur, user, day=5):
    """
    Находит все обращения по которым пользователи не отвечают больше 5 дней.
    Выдает список таких обращений.
    :param cur: курсор к БД
    :param user: ИД пользователя
    :return: список обращений
    """
    # время, после которого обращение ставим в список
    t = datetime.timedelta(days=day)
    now = datetime.datetime.today()
    waitList = list()
    # получаем список всех обращений в статуса рассматривается
    cur.execute('SELECT id FROM Obr WHERE UserId = ? and StatusObrId = 3', (user,))
    obrList = cur.fetchall()
    for i in obrList:
        obr = i[0]
        # Получаем дату последнего комментария и номер пользователя который его оставил
        cur.execute('SELECT top 1 dt, UserId FROM ObrComment where ObrId = ? order by dt desc', (obr,))
        res = cur.fetchone()
        if res:
            # есть комментарии, проверим дату, чтобы была больше указанной
            if now - res[0] > t :
                # проверим, чтобы комментарий был от нас
                res = cur.execute('select UserTypeId from Users where id = ?', (res[1],)).fetchone()
                if res:
                    if res[0] == 1:
                       # да это наш комментарий
                       waitList.append(str(obr))
    return waitList


def findNew(cur, user):
    """Находит все обращения специалиста в статусе новые
    :param cur: курсор
    :param user: специалист
    :return: список номеров обращений
    """
    newList = list()
    # получаем список всех обращений в статуса новое
    cur.execute('SELECT ID FROM Obr WHERE UserId=? AND StatusObrId = 1', (user,))
    obrList = cur.fetchall()
    for i in obrList:
        newList.append(str(i[0]))
    return newList


def findNoWork(cur, user):
    """Находит все обращения специалиста в статусе принято, старше 5 дней
    :param cur: курсор
    :param user: специалист
    :return: список номеров обращений
    """
    obrList = list()
    # получаем список всех обращений в статуса новое
    cur.execute('SELECT ID FROM Obr WHERE UserId=? AND StatusObrId = 4 AND DATEADD(DAY,5,DatObr) <=GETDATE()', (user,))
    tempList = cur.fetchall()
    for i in tempList:
        obrList.append(str(i[0]))
    return obrList


if __name__ == '__main__':
    """Направляет следующие напоминания:
    1) Если у пользователя стоит Рассматривается = 1, то находит обращения, по которым уже идет работа,
    а они висят в статусе новое или принято. Меняет им статус на Рассматривается
    2) Ищет все обращения пользователя со статусом задания выданы, у которых все задания закрыты выполенны или
    отменены и предалгает их закрыть.
    3) Находит все обращения по которым пользователи не отвечают больше 5 дней
    4) Находит все обращения в статусе новые.
    5) Находит все обращения висящие в статусе принято более 5 дней.
    """
    # читаю конфигурационный файл
    DB, users, work, err = config.readConfig()
    if err:
        exit(1)
    # проверяю конфигурационный файл
    err = config.configValidator(DB, users, work)
    d = work['noActiveObr']
    if err:
        print('В конфигурационном файле найдена ошибка(и):', err)
        exit(1)
    # пробуем соединится с БД
    try:
        con = pypyodbc.connect('DRIVER=FreeTDS; SERVER=%s; PORT=%s; DATABASE=%s; UID=%s; PWD=%s; TDS_Version=8.0; ClientCharset=UTF8;'
                               % (DB['adr'], DB['port'], DB['name'], DB['user'], DB['pwd']))
        cur = con.cursor()
    except :
        print("Возникла ошибка при соединении с БД")
        exit(1)
    # прочитать токен  для робота
    with open('token.txt', mode='r', encoding='utf-8') as fp:
        testToken = fp.read()
    slack = Slacker(testToken)
    # перебираем пользователей
    for user in users:
        msg = ""
        print('Работает с пользователем:', user['name'])

        # отрабатываем корректировку в РАБОТЕ
        if user['correct1']:
            # если указано в настройках, отрабатываем корректировку
            correctList = obrValid1(cur, user['id'])
            if correctList:
                msg += """Есть обращения по которым идет работа, но они все еще висят в статусе новое или принято: %s.
Их статус был автоматически заменен на Рассматривается\n""" % '; '.join(correctList)
                con.commit()
            else:
                msg += 'Обращений, по которым идет работа, но статус новое или принято: нет.\n'
        else:
            msg += "Проверка по наличию обращению с идущей работой и статусом новое или принято отключена.\n"


        # отрабатываем информирование по заданиям в обращении
        complite, text = obrJobComplete(cur, user['id'])
        msg += text
        if complite:
            print(complite)
            msg += 'Есть обращения, которые можно закрыть т.к. выполнены все задания: %s \n' % '; '.join(complite)
        else:
            msg +="Не закрытых обращений с выполненными заданиями нет.\n"

        # находим обращения, по котором пользователи не отвечали больше 5 дней
        n = obrValid2(cur, user['id'], d)
        if n:
            msg += 'Предлагаю закрыть эти указанные обращения, по ним пользователи не отвечали более %s дней: %s\n' \
            % (d, '; '.join(n))
        else:
            msg += 'Обращений в которых пользователи не активны более %s дней нет\n' % d

        # находим все новые обращения
        n = findNew(cur, user['id'])
        if n:
            msg += 'Есть новые обращения (%s шт): %s\n' % (len(n), '; '.join(n))
        else:
            msg += 'Обращений в статусе новое нет.\n'

        # находим обращения, которые висят в принято больше 5 дней
        n = findNoWork(cur, user['id'])
        if n:
            msg += 'Обращения висят в принято больше 5 дней (%s шт): %s\n' % (len(n), '; '.join(n))
        else:
            msg += 'Обращений висящих в принято больше 5 дней нет.\n'

        # сохраним для истории
        fileName = 'msg/'+user['name']
        open(fileName, mode='w').write(msg)
        # отправка
        if user['jabber']:
            # указан jabber, шлю туда
            p = subprocess.Popen("""cat "%s" | sendxmpp %s""" % (fileName, user['jabber']), shell=True)
            # ждем завершения
            p.wait()
        elif user['slack']:
            #pass
            # указан шлак, шлем сюда
            slack.chat.post_message('@'+user['slack'], msg, as_user=True)
        else:
            # не указан - на печать
            print(msg)
    con.close()
    exit(0)
