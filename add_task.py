# -*- coding: utf-8 -*-
import config
import pypyodbc
import platform
import datetime
import leaders
import project_files
import re
import glob
import os
import csv


"""
Добавляет задания из файла CSV
"""
sh = re.compile(r'\(.*\)')


def get_name(tj_name):
    """
    Получает имя пользователя из формата tj. Фактически удаляя кусок с скобками
    :param tj_name:
    :return: user_name
    """
    user_name_list = list()
    for i in tj_name.split(sep=' '):
        if not (i.find('(')>-1 and i.find(')')>-1):
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
    dpr_id = 0
    name = name.lower()
    for user in users:
        if user['name'].lower() == name:
            dpr_id = user['id']
            break
    return dpr_id


if __name__ == '__main__':
    DB, users, work, imap, err = config.readConfig()
    if err:
        exit(1)
    # Соединение с БД
    #con = leaders.get_сonnect(DB)
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
                task_for_dpr['WorkTypeId'] = 1
                # Название задания
                task_for_dpr['name'] = i[1].strip()
                # Кто тестирует
                task_for_dpr['UserTestId'] = 2
                # Кто делает
                task_for_dpr['UserDevelopId'] = dpr_id
                # Статус задания 1 - задание выдано
                task_for_dpr['StatusId'] = 1
                # Какой проект
                task_for_dpr['ProjectId'] = project_info['id']
                # ИД региона
                task_for_dpr['regionId'] = project_info['name']
                tasks_for_dpr.append(task_for_dpr)
        csv_file.close()
        # Будем добавлять задания

        # Проверить, вдруг такое задание уже есть. В этом случае добавлять не будем

        # Если задания нет, то показать пользователю что получилось

        # и спросить добавлять или нет

        # добавляем задание

        # добавляем к нему комментарий


        '''
                      insert Tasks (WorkTypeId, name, UserStartId , UserTestId, UserDevelopId, StatusId, ProjectId, dateStart, planDate)
VALUES (1, "Название задания", 2, 2, 'кто разработчик', 1, 'название проекта', 'дата выдачи', 'дата выполнения');
                    комментарий -   insert TaskComment (taskid, comment, dt, userid) VALUES (1, '', '', 2)

        '''


        #con.close()
        #"""
