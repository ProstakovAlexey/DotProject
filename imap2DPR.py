# -*- coding: utf-8 -*-

import imaplib
import email
import datetime
import logging
import re
import time
import im_d
import html2text
import config
import leaders

""" Программа предназначена для работы с почтой и дотпроджект.
Она должна запускаться по расписанию (cron), не реже раза в день, желательно
каждые 15 мин.
1) После запуска соединяется с IMAP сервером, скачивает заголовки всех писем из
папки Простаков за последний день.
2) Если в заголовке нет номера обращения в ДПР, то программа выполняет:
    а) добавляет в ДПР обращение за текущую дату;
    б) к созданному обращению добавляет комментарий (тело письма);
    в) в тему письма (на IMAP сервере) добавляет номер обращения
Действия программы логируются в папке logs. В рабочем режиме желательно логирование
переключить в уровень ERROR.
"""


def get_from_addr(headers_dict):
    """
    Получает обратный адрес из поля From. Расчитавает на то, что в адресе есть @,
    а в имени ее нет. Так же в адресе не должно быть знаков < и >.
    Вход: словарь заголовков
    Выход: строка с адресом
    """
    # Можно было рег. выражением сделать, но пока и так работает
    from_addr = None
    # Заменим < т.к. некоторые почтовики не делают пробела между именем и <
    for word in search_header(headers_dict, 'From').replace('<', ' ').split(' '):
        if word.find(r'@') > 0:
            from_addr = word
            break
    return from_addr.replace('>', '').replace('"', '').replace("'", '').strip()


def get_box_name(im_box):
    """
    Служебная функция, может вывести на экран названия всех imap папок
    вложенных в inbox.
    Нужно, что выбрать интересующую.
    Вход: соединение с imap сервером
    """
    for i in im_box.list('INBOX')[1]:
        a = i.decode().split('INBOX.')[-1]
        print(a, '----', im_d.decoder(a))


def search_header(headers, string='Subject'):
    """
    Ищет указанный заголовок в письме
    Вход: распарсенное email, название заголовка.
    Выход: заголовок в строке, если не найден None
    """
    result = ''
    try:
        for subj in email.header.decode_header(headers[string]):
            # в 0 части сам заголовок, в 1 - кодировка
            if subj[1] is None:
                # Если кодировка не указана, отдаем как есть. Нам повезет!
                res = subj[0]
            else:
                # Декодируем с указанной кодировкой
                try:
                    res = subj[0].decode(subj[1])
                except:
                    # Кодировку указали не правильную
                    print("Произошла ошибка декодирования заголовка")
                    res = subj[0]
            result += str(res)
    except:
        # Был случай, что заголовка не было!
        pass
    return result


def get_decoded_email_body(part):
    """Декодирует тело сообщения в обычную строку utf-8.
    Если тело html то преобразует в текст.
    Если сообщение мультипатрт, то берет первую часть """

    text = "Робокот не смог прочесть тест письма"
    # возможны вложенные в первое письмо, дополнительные письма
    while part.is_multipart():
        # будем копать до последнего
        part = part.get_payload(0)
    # Определяем кодироку
    if part.get_charsets()[0] is None:
        # если кодировки нет, то отдаем как есть
        text = part.get_payload(decode=True)
    else:
        # кодировка есть
        charset = part.get_content_charset()
        # это простой текст
        if part.get_content_type() == 'text/plain':
            # получает строку, переводит ее в уникод, с заданной кодировкой
            text = part.get_payload(decode=True).decode(charset, "ignore")
            # возможно это html
        elif part.get_content_type() == 'text/html':
            html = part.get_payload(decode=True).decode(charset, "ignore")
            # html2text возвращает строку в unicode
            text = html2text.html2text(html)
            # случилось что-то странное
        else:
            logging.error('Тело сообщения не txt и не html')
    return text


# Будет создавать новый лог файл каждый день
log_file_name = r'logs/'+datetime.datetime.today().strftime(r'%Y-%m-%d') + r'_Добавить_в_ДПР.log'
logging.basicConfig(filename=log_file_name, filemode='a', level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s: %(message)s')
logging.info('Запуск программы поиска писем для добавления в ДПР.')

# Шаблоны для поиска DPR в теме
sh = re.compile("DPR:\d\d\d\d\d", re.I)
sh1 = re.compile("DPR:\s\d\d\d\d\d", re.I)


# Читаю конфигурационный файл
DB, users, work, imap, err_message = config.readConfig()
if err_message:
    logging.critical(err_message)
    exit(1)
# Соединение с БД
con, err_message = leaders.get_сonnect(DB)
# При соединении возникла ошибка, закончим работу
if err_message:
    logging.critical(err_message)
    exit(1)
logging.debug('Успешно соединились с БД')
cur = con.cursor()

# Соединение с почтовым сервером
M = imaplib.IMAP4(host=imap['host'])
res = M.login(imap['user'], imap['password'])
'''
# Вывести все папки в inbox
get_box_name(M)
exit(2)
'''

if res[0] != 'OK':
    logging.critical('Ошибка при соединении с imap сервером: %s' % res)
    con.close()
    exit(2)
logging.debug('Успешно соединился с imap сервером.')

# Список пользователей для обработки: (папка, UserId в ДПР, вид обращения, имя)

"""
users = list()
# Простаков
users.append(('INBOX.&BB8EQAQ+BEEEQgQwBDoEPgQy-', 2, 3, 'Простаков А.Н.'))
# Валиулин
users.append(('INBOX.&BBIEMAQ7BDgEQwQ7BDgEPQ-', 73, 3, 'Валиулин О.Б.'))
# Ларькин
users.append(('INBOX.&BBsEMARABEwEOgQ4BD0-', 235, 3, 'Ларкин Д.Б.'))
# Сеньчев
users.append(('INBOX.&BCEENQQ9BEwERwQ1BDI-', 404, 1, 'Сеньчев Евгений'))
# Чиркова
users.append(('INBOX.&BCcEOARABDoEPgQyBDA-', 30, 1, 'Чиркова Анастасия'))
# Артюхова
users.append(('INBOX.&BBAEQARCBE4ERQQ+BDIEMA-', 13, 1, 'Артюхова Лариса'))
# Сеньчева
users.append(('INBOX.&BCEENQQ9BEwERwQ1BDIEMA-', 25, 3, 'Сеньчева Надежда Юрьевна'))
# Рысаев Расул
users.append(('INBOX.&BCAESwRBBDAENQQy-', 394, 1, 'Рысаев Расул'))
"""
for user in users:
    if not (user['imap'] and user['new_obr']):
        logging.debug('Пользователь %s не участвует в автоматическом создании новых обращений' % user['name'])
        continue
    logging.debug('Обрабатываю пользователя: %s' % user['name'])
    # Выбирает нужную папку
    res = M.select(mailbox=user['imap'], readonly=False)
    if res[0] != 'OK':
        logging.critical('Ошибка при переходе в папку: %s' % res[0])
        con.close()
        M.close()
        M.logout()
        exit(3)
    logging.debug('Успешно перешел в папку.')

    # Получает id писем по фильтру
    # Указывает за сколько времени смотреть
    date = (datetime.datetime.today() - datetime.timedelta(days=imap['days']))
    rule = '(SENTSINCE {date})'.format(date=date.strftime("%d-%b-%Y"))
    logging.debug('Получаю номера писем по фильтру: %s' % rule)
    ok, email_id = M.search(None, rule)
    if ok == 'OK':
        for num in email_id[0].split():
            # Получаем заголовки писем
            typ, headers = M.fetch(num, '(BODY.PEEK[HEADER])')
            # Вытаскиваем только заголовки, т.к. тело не получали
            header_dict = email.message_from_bytes(headers[0][1])

            # Пытаемся получить тему
            subj = search_header(header_dict, 'Subject')
            if subj == '':
                subj = 'АСП'
            logging.debug('Получил заголовок для письма: ID=%s дата=%s тема=%s.' %
                          (header_dict['Message-ID'], header_dict['Date'], subj))

            # Поищем в теме DPR
            if sh.search(subj) or sh1.search(subj):
                # Нашли,делать с эти письмом ничего не будем
                logging.debug('Нашел номер обращения в теме.')
                # Эта команда сразу начинает новую итерацию цикла
                continue
            logging.debug('Не нашел номер обращения в теме.')

            # Номер не нашли, буду добавлять его в ДПР
            # Получим адрес отправителя
            from_addr = get_from_addr(header_dict)
            if from_addr is None:
                logging.error('В письме Дата=%s Тема=%s не нашли адрес. Пропускаю его.'
                              % (header_dict['Date'], subj))
                continue

            # Поищем в таблице пользователя с таким адресом
            sql = 'select id, name, regiontypeid from users \
                where email like(\'%s\')' % ('%' + from_addr + '%')
            # print(sql)
            cur.execute(sql)
            res = cur.fetchone()
            if res is None:
                logging.error('Не нашли в ДПР пользователя с email=%s, добавьте его. '
                              'Пока письмо от него будет пропущено.' % from_addr)
                continue

            # Добавим обращение, выполним усечение данных
            cur.execute("""insert into Obr (userid, vidobrid, question, datobr,
                regionid, fio, obruserid, statusobrid, targetobrtypeid)
                values (?, 1, ?, ?, ?, ?, ?, 3, ?)""", (user['id'], subj[:100], datetime.datetime.today(),
                                                        res[2], res[1], res[0], user['new_obr']))
            con.commit()
            # Номер созданного обращения
            obr_id = cur.execute('SELECT @@IDENTITY').fetchone()[0]
            if obr_id > 0:
                logging.info('Добавил обращение %s.' % obr_id)
            else:
                logging.error('Не смог добавить обращение.')
                continue
            # К уже созданному обращению прибавим комментарий - тело письма.
            # Приложенные к письму файлы не добавляются. Скачиваем письмо целиком
            typ, msg = M.fetch(num, '(RFC822)')
            # Парсим письмо
            msg = email.message_from_bytes(msg[0][1])
            # Получаем тело
            body = get_decoded_email_body(msg)
            # Записать в обращение
            cur.execute("INSERT INTO ObrComment (ObrId,comment,dt,UserId) VALUES (?, ?, GETDATE(), 171)",
                        (obr_id, body))
            con.commit()
            logging.info('Записал комментарий к обращению %s' % obr_id)

            '''Будем добавлять номер обращения в тему. К сожалению в imap
            отредактировать письмо нельзя, его можно только удалить и вставить
            потом новое (измененное)'''
            # Заменяем заголовок
            try:
                msg.replace_header('Subject', '%s DPR:%s' % (subj, obr_id))
            except:
                logging.error('Ошибка при замене темы, добавим тему')
                msg.add_header('Subject', '%s DPR:%s' % (subj, obr_id))
            # Отправляем измененное сообщение на сервер
            res = M.append(user['imap'], flags='',
                           date_time=time.localtime(), message=msg.as_bytes())
            if res[0] == 'OK':
                # Добавили успешно, удалить оригинал
                logging.debug('Добавили успешно.')
                res = M.store(num, '+FLAGS', '\\Deleted')
                if res[0] == 'OK':
                    logging.debug('Отметили оригинал к удалению.')
                else:
                    logging.error('Не удалось отметить сообщения для удаления.'
                                  'Ошибка: %s.' % res[0])

            else:
                logging.error('При добавлении сообщения на imap сервер возникла ошибка: %s.' % res[0])
                # break
    else:
        logging.error('Писем для %s получить не удалось.' % user['name'])
    # Удаляем отмеченные
    res = M.expunge()
    if res[0] == 'OK':
        logging.debug('Отмеченные сообщения удалены.')
    else:
        logging.error('Отмеченные сообщения не удалены. Ошибка: %s.' % res)
# Закрывает соединение с imap сервером
M.close()
M.logout()
con.close()
logging.info('Программа работу закончила.')
exit(0)
