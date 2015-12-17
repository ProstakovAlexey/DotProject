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
        # получаем список пользователей к этому обращению, у которых тип=1 (социнформтех)
        cur.execute("""select count(id) from Users where id in
        (SELECT DISTINCT userId FROM ObrComment where ObrId = ?) and Users.UserTypeId=1""", (obr,))
        # есть хотя бы один пользователь
        if cur.fetchone()[0] > 0:
            correctList.append(obr)
            cur.execute('update Obr set StatusObrId = 3 where Id = ?', (obr,))

    return correctList


if __name__ == '__main__':
    # читаю конфигурационный файл
    DB, users, err = config.readConfig()
    if err:
        exit(1)
    # проверяю конфигурационный файл
    err = config.configValidator(DB, users)
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
        print('Работает с пользователем:', user['name'])

        # отрабатываем корректировку в РАБОТЕ
        if user['correct1']:
            # если указано в настройках, отрабатываем корректировку
            correctList = obrValid1(cur, user['id'])
            if correctList:
                print("""Есть обращения по которым идет работа, но они все еще висят в статусе новое или принято: %s.
Их статус был автоматически заменен на Рассматривается""" % correctList)
                con.commit()
            else:
                print('Обращений, по которым идет работа, но статус новое или принято нет.')

        # отрабатываем информирование по заданиям в обращении
        complite = obrJobComplete(cur, user['id'])
        if complite:
            print('Есть обращения, которые можно закрыть т.к. выполнены все задания:', complite)
        else:
            print("Незакрытых обращений с выполненными заданиями нет.")

    con.close()
    exit(0)