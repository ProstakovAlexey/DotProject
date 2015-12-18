# coding=utf8
__author__ = 'Prostakov Alexey'
"""
Описание
**********************

Входные данные
**********************

Выходные данные
**********************

"""
# библиотека для работы с БД
import pypyodbc
import config
import subprocess
import datetime


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
    # получаем список обращений пользователя со статусом задания выданы
    cur.execute('SELECT id FROM Obr WHERE UserId = ? and StatusObrId = ?', (user, 6))
    complete = list()
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
                complete.append(obr)
        else:
            print('Ошибка в обращении %s. Установлен статус задания выданы, а ни одного задания нет' % obr)
    return complete


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
            correctList.append(obr)
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
                cur.execute('select UserTypeId from Users where id = ?', (res[1],))
                if cur.fetchone()[0] == 1:
                    # да это наш комментарий
                    waitList.append(obr)
    return waitList


if __name__ == '__main__':
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
Их статус был автоматически заменен на Рассматривается\n""" % correctList
                con.commit()
            else:
                msg += 'Обращений, по которым идет работа, но статус новое или принято: нет.\n'
        else:
            msg += "Проверка по наличию обращению с идущей работой и статусом новое или принято отключена.\n"


        # отрабатываем информирование по заданиям в обращении
        complite = obrJobComplete(cur, user['id'])
        if complite:
            msg += 'Есть обращения, которые можно закрыть т.к. выполнены все задания: %s \n' % complite
        else:
            msg +="Незакрытых обращений с выполненными заданиями нет.\n"

        # находим долгие обращения
        msg += 'Предлагаю закрыть эти указанные обращения, по ним пользователи не отвечали более %s дней: %s' % \
              (d, obrValid2(cur, user['id'], d))

        # печать результата
        if user['jabber']:
            # указан jabber, жлю туда
            fileName = 'jabberMsg/'+user['name']
            open(fileName, mode='w').write(msg)
            p = subprocess.Popen("""cat "%s" | sendxmpp %s""" % (fileName, user['jabber']), shell=True)
            # ждем завершения
            p.wait()
        else:
            # не указан - на печать
            print (msg)

    con.close()
    exit(0)