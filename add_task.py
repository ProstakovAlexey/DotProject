# -*- coding: utf-8 -*-
import config
import datetime
import leaders
import glob
import os
import csv

"""
Добавляет задания в ДПР из файла CSV
"""


def get_name(tj_name):
    """
    Получает имя пользователя из формата tj. Фактически удаляя кусок с скобками
    :param tj_name:
    :return: user_name
    """
    user_name_list = list()
    for i in tj_name.split(sep=' '):
        if not (i.find('(') > -1 and i.find(')') > -1):
            # Это не кусок со скобками, любимый tj, его буду включать
            user_name_list.append(i)
    return ' '.join(user_name_list)


def get_dpr_id(name, users):
    """
    Ищет id пользователя ДПР, по его имени
    :param name: имя из csv файла
    :param users: словарь с пользователя
    :return: id или 0 (если не нашел)
    """
    user_dpr_id = 0
    name = name.lower()
    for user in users:
        if user['name'].lower() == name:
            user_dpr_id = user['id']
            break
    return user_dpr_id


def task_print(task):
    """
    Выдает строку с информацией о задании, которое предполагается добавить
    :param task: словарь с заданием
    :return: строка для печати
    """
    result = '''Тема: {0}
    Название: {1}
    Выдал: {2},
    Делает: {3},
    Тестирует: {4},
    Начало: {5},
    Окончание: {6}
    Комментарий: {7}
    '''.format(task['project_id'], task['name'], task['user_start_id'], task['user_develop_id'],
               task['user_test_id'], task['date_start'], task['date_plan_end'], task_for_dpr['note'])
    return result


def add_task_into_dpr(task_dict, cursor):
    """
    Добавляет задание в ДПР, вместе с его комментарием
    :param task_dict: задание
    :param cursor: курсок
    :return: номер задания
    """
    cursor.execute('insert Tasks (WorkTypeId, name, UserStartId , UserTestId, UserDevelopId, '
                'StatusId, regionId, TopicId, dateStart, planDate, PriorTypeId)'
                'VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, 4)',
                   (task_dict['name'], task_dict['user_start_id'], task_dict['user_test_id'],
                    task_dict['user_develop_id'], task_dict['status_id'], task_dict['region_id'],
                    task_dict['project_id'], task_dict['date_start'], task_dict['date_plan_end']))
    cursor.commit()
    task_id = task_find(task_dict, cursor)
    cursor.execute('INSERT TaskComment (taskid, comment, dt, userid) VALUES (?, ?, ?, ?)',
                   (task_id, task_dict['note'], datetime.datetime.now(), task_dict['user_start_id']))
    cursor.commit()
    return task_id


def task_find(task, cursor):
    """
    Ищет задание в БД, если находит возвращает его ID. Если нет - 0
    :param task: словарь с заданием
    :param cursor: курсок к БД
    :return: ID или 0
    """
    task_id = 0
    cursor.execute('SELECT id FROM Tasks WHERE name=? AND TopicId=?', (task['name'], task['project_id']))
    res = cursor.fetchone()
    if res:
        task_id = res[0]
    return task_id


if __name__ == '__main__':
    DB, users, work, imap, err = config.readConfig()
    if err:
        exit(1)
    # Соединение с БД
    con, err_msg = leaders.get_сonnect(DB)
    if err_msg:
        print(err_msg)
        exit(1)
    cur = con.cursor()
    # Находим все project_files файлы в каталоге project_files
    for file in glob.glob('project_files/*.csv'):
        csv_file_name = os.path.split(file)[1]
        # Проверим, если для него конфигурационный файл, если нет, то не буду обрабатывать
        ini_file_name = csv_file_name.replace('.csv', '.ini')
        if not os.path.exists(os.path.join('project_files', ini_file_name)):
            print('Для файла {0} нет файла описателя {1}. Его обработка не будет выполнена.'
                  .format(csv_file_name, ini_file_name))
            compile()
        print('Выполняю обработку файла {0} и его описателя {1}'.format(csv_file_name, ini_file_name))

        # Прочитаем свойства проекта
        project_info, err_msg = config.read_proj_info(os.path.join('project_files', ini_file_name))
        if err_msg:
            print('Ошибка при обработке {} - {}. Проект будет пропущен.'.format(ini_file_name, err_msg))
            continue

        # Читаю csv файл
        csv_file = open(os.path.join('project_files', csv_file_name), encoding='utf-8', newline='\n')
        task_reader = csv.reader(csv_file, delimiter=';')
        # Этот словарь накапливает информацию для создания заданий, я сразу их не создаю, т.к. это может
        # быть опасно. Создание только после подтверждения от пользователя
        tasks_for_dpr = list()
        for i in task_reader:
            if i[2]:
                # Если исполнитель не равен равен нулю, то поищем его id
                csv_user_name = get_name(i[2])
                dpr_id = get_dpr_id(csv_user_name, users)
                if dpr_id == 0:
                    print('Пользователя [%s] не нашли в ДПР. Возможно у него перепутано имя, проверьте' % csv_user_name)
                    continue
                task_for_dpr = dict()
                # Доработка
                task_for_dpr['work_type_id'] = 1
                # Название задания
                task_for_dpr['name'] = i[1].strip()
                # Кто выдал
                task_for_dpr['user_start_id'] = 2
                # Кто тестирует
                task_for_dpr['user_test_id'] = 2
                # Кто делает
                task_for_dpr['user_develop_id'] = dpr_id
                # Статус задания 1 - задание выдано
                task_for_dpr['status_id'] = 1
                # Какой проект
                task_for_dpr['project_id'] = project_info['project_id']
                # ИД региона
                task_for_dpr['region_id'] = project_info['reg_id']
                # Начало
                task_for_dpr['date_start'] = datetime.datetime.strptime(i[3], "%d-%m-%Y %H:%M")
                # Окончание плановое
                task_for_dpr['date_plan_end'] = datetime.datetime.strptime(i[4], "%d-%m-%Y %H:%M")
                task_for_dpr['note'] = i[5].strip()
                tasks_for_dpr.append(task_for_dpr)
        csv_file.close()
        # Будем добавлять задания
        for task_for_dpr in tasks_for_dpr:
            # Проверить, вдруг такое задание уже есть. В этом случае добавлять не будем
            if task_find(task_for_dpr, cur):
                print('Такое задание уже есть, но не будет добавлено')
                continue
            # Если задания нет, то показать пользователю что получилось
            print('Предлагаю добавить задание:\n {}'.format(task_print(task_for_dpr)))
            # и спросить добавлять или нет
            answer = input('Добавить это задание?(y/n)').lower()
            if answer == 'y' or answer == 'н':
                # добавляем задание
                print('Добавил, задание №%s' % add_task_into_dpr(task_for_dpr, cur))
    con.close()
    print('Программа работу закончила')
    exit(0)
