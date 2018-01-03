#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""Содержит несколько тестов, для проверки работоспособности программы"""

import unittest
import add_task
import config
import os


class СaseGetName(unittest.TestCase):
    """Класс предназначен для проверки функций получающей имена из файл csv"""
    def test1(self):
        """Проверяет типичный для tj случай со скобками, если есть ФИО"""
        tj_name = 'Простаков Алексей Николаевич (alex)'
        user_name = 'Простаков Алексей Николаевич'
        result = add_task.get_name(tj_name)
        msg = 'Для входных данных {0} ожидали получить {1}, а получили {2}'.format(tj_name, user_name, result)
        self.assertEqual(user_name, result, msg)

    def test2(self):
        """Проверяет типичный для tj случай со скобками, если есть ФИ"""
        tj_name = 'Простаков Алексей (alex)'
        user_name = 'Простаков Алексей'
        result = add_task.get_name(tj_name)
        msg = 'Для входных данных {0} ожидали получить {1}, а получили {2}'.format(tj_name, user_name, result)
        self.assertEqual(user_name, result, msg)

    def test3(self):
        """Проверяет случай если файл сформирован вручную и скобок нет, если есть ФИО"""
        tj_name = 'Простаков Алексей Николаевич'
        user_name = 'Простаков Алексей Николаевич'
        result = add_task.get_name(tj_name)
        msg = 'Для входных данных {0} ожидали получить {1}, а получили {2}'.format(tj_name, user_name, result)
        self.assertEqual(user_name, result, msg)

    def test4(self):
        """Проверяет случай если файл сформирован вручную и скобок нет, если есть ФИ"""
        tj_name = 'Простаков Алексей'
        user_name = 'Простаков Алексей'
        result = add_task.get_name(tj_name)
        msg = 'Для входных данных {0} ожидали получить {1}, а получили {2}'.format(tj_name, user_name, result)
        self.assertEqual(user_name, result, msg)

    def test5(self):
        """Проверяет случай если файл сформирован вручную и скобок нет, если есть ФИ и скобки слитно.
        Обратите внимание, что отбрасывает все слово со скобками"""
        tj_name = 'Простаков Алексей(регион)'
        user_name = 'Простаков'
        result = add_task.get_name(tj_name)
        msg = 'Для входных данных {0} ожидали получить {1}, а получили {2}'.format(tj_name, user_name, result)
        self.assertEqual(user_name, result, msg)


class СaseReadProjectConfig(unittest.TestCase):
    """Класс предназначен для проверки функций чтения конфигурационного файла"""
    def test1(self):
        """Проверяет аккуратный файл"""
        file_name = 'project_info_1.ini'
        good = {'project_id': 193, 'reg_id': 23}
        result, err_msg = config.read_proj_info(os.path.join('tests_data', file_name))
        self.assertFalse(err_msg, 'Должно было прийти пустое сообщение об ошибке')
        self.assertEqual(good, result)

    def test2(self):
        """Проверяет файл, где случайно добавили к имени региона пробел"""
        file_name = 'project_info_2.ini'
        good = {'project_id': 193, 'reg_id': 23}
        result, err_msg = config.read_proj_info(os.path.join('tests_data', file_name))
        self.assertFalse(err_msg, 'Должно было прийти пустое сообщение об ошибке')
        self.assertEqual(good, result)

    def test3(self):
        """Конфигурационный файл не найден"""
        file_name = 'project_info_3.ini'
        result, err_msg = config.read_proj_info(os.path.join('tests_data', file_name))
        self.assertEqual(err_msg, r'Конфигурационный файл tests_data\project_info_3.ini не найден')

    def test4(self):
        """ini файл не содержит секции [PROJECT], он в неправильном формате"""
        file_name = 'project_info_4.ini'
        result, err_msg = config.read_proj_info(os.path.join('tests_data', file_name))
        self.assertEquals(err_msg, 'Свойство проекта project_id не может быть пустым. ')

    def test5(self):
        """ini файл не содержит секции [PROJECT], он в неправильном формате"""
        file_name = 'project_info_5.ini'
        result, err_msg = config.read_proj_info(os.path.join('tests_data', file_name))
        self.assertEquals(err_msg, 'Свойство проекта reg_id не может быть пустым. ')



