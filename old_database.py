# -*- coding: utf-8 -*-
import datetime
import logging
import leaders
from slacker import Slacker


if __name__ == '__main__':
    # Готовит список БД
    log_file_name = r'logs/' + datetime.datetime.today().strftime(r'%Y-%m-%d') + '_Старые_БД.log'
    logging.basicConfig(filename=log_file_name, filemode='a', level=logging.DEBUG,
                        format='%(asctime)s %(levelname)s: %(message)s')
    # Настройка для соединения с БД
    db = {'name': 'master', 'adr': 'AN', 'port': '1433', 'user': 'sa', 'pwd': '111'}
    # Соединение с БД
    con, err_message = leaders.get_сonnect(db)
    # При соединении возникла ошибка, закончим работу
    if err_message:
        logging.critical(err_message)
        exit(1)
    logging.debug('Успешно соединились с сервером БД')
    cur = con.cursor()
    # Получить список БД на AN
    cur.execute("select a.id, a.alias from master..listdb a inner join master..LISTSERVER b on"
                " a.SERVERID=b.ID inner join sys.databases x on x.name = a.alias where b.NAME='AN' order by a.id")
    db_list = list()
    for line in cur.fetchall():
        db_list.append(line)
    con.close()
    logging.debug('Получил список БД: %s' % db_list)
    now = datetime.datetime.now()
    # Как давно не заходили
    delta = datetime.timedelta(days=40)
    count = 0
    message = 'БД на AN, в которые не заходили 40 дней и больше: \n'
    # Получаю в каждой протокол
    for db_info in db_list:
        # Подключаемся к нужной БД
        db['name'] = db_info[1]
        con, err_message = leaders.get_сonnect(db)
        if err_message:
            print(db_info[1], err_message)
        else:
            cur = con.cursor()
            cur.execute("SELECT top 1 change_date from protocol where work_id=414 order by change_date desc")
            result = cur.fetchone()
            # Удивительно, но протокол может быть пустой
            if result:
                if now-result[0] >= delta:
                    count += 1
                    message += 'ИД: {2}, БД: {0}, последний вход: {1}\n'\
                        .format(db_info[1], result[0].strftime('%d.%m.%Y'), db_info[0])
            else:
                message += 'ИД: {0}, БД: {1}, протокол пустой, считаю что в нее ни кто не заходил вообще.\n' \
                    .format(db_info[0], db_info[1])
            # Закрыть соединение
            con.close()
    if count:
        message += '--------------------------------------\n'
        message += 'Всего: {0}'.format(count)
    else:
        message += 'таких БД нет, все шито-крыто!'
    logging.debug(message)
    # Прочитать токен  для робота
    with open('token.txt', mode='r', encoding='utf-8') as fp:
        token = fp.read()
    slack = Slacker(token)
    logging.debug('Соединился со slack')
    # Отправляю сообщение
    #slack.chat.post_message('#fortestintegration', message, as_user=True)
    logging.info('Программа работы закончила')
    exit(0)
