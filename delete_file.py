from slacker import Slacker
import datetime

"""
Удаляет ненужные файлы из slack
"""
time_delta = datetime.timedelta(days=7)


if __name__ == '__main__':
    with open('token.txt', mode='r', encoding='utf-8') as fp:
        testToken = fp.read()
    slack = Slacker(testToken)
    print('Соединился со Slack')
    file_list = slack.files.list().body
    pages = file_list['paging']['pages']
    print('Всего %s страниц файлов' % pages)
    total_size = 0
    total_del = 0
    for page in range(0, pages):
        print('Страница:', page)
        file_list = slack.files.list(page=page).body['files']
        for f in file_list:
            f_info = slack.files.info(file_=f['id'])
            f_t = datetime.datetime.fromtimestamp(f_info.body['file']['timestamp'])
            f_n = f_info.body['file']['name']
            if datetime.datetime.now() - f_t > time_delta:
                print('Можно удалить:', f_n, f_t)
                try:
                    slack.files.delete(f['id'])
                except:
                    print('Файл удалить не удалось')
                    break
                else:
                    print('Удален')
                    total_del += 1
                    total_size += f_info.body['file']['size']
    print('Всего удалено файлов: {0}, общий размер {1}Мб'.format(total_del, int(total_size/1024/1024)))







