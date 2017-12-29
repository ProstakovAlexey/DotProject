# -*- coding: utf-8 -*-
import config
import pypyodbc
import platform
import datetime
import obr_analiz
import csv
import re


"""
Добавляет задания из файла CSV
"""
users_id = {'alex': 2, 'dima': 345, 'andrey': 20}
sh = re.compile(r'\(.*\)')


if __name__ == '__main__':
    DB, users, work, err = config.readConfig()
    print(users)
    if err:
        exit(1)
    # Соединение с БД
    con = obr_analiz.getConnection(DB)
    # Читает данные из CSV файла
    csvfile = open('csv.csv', encoding='utf-8', newline='\n')
    task_reader = csv.reader(csvfile, delimiter=';')
    for i in task_reader:
        if i[2] is not None:
            # Не равен нулю, проверим какой id
            name = sh.findall(i[2])[0]
            if name is not None:
                name = name.replace('(', '').replace(')', '')
                if name is users_id:
                    dpr_id = users_id[name]
                    '''
                      insert Tasks (WorkTypeId, name, UserStartId , UserTestId, UserDevelopId, StatusId, ProjectId, dateStart, planDate)
VALUES (1, "Название задания", 2, 2, 'кто разработчик', 1, 'название проекта', 'дата выдачи', 'дата выполнения');
                    комментарий -   insert TaskComment (taskid, comment, dt, userid) VALUES (1, '', '', 2)

                    '''


    csvfile.close()
    con.close()