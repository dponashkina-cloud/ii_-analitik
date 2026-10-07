"""
Описание функций для GigaChat (function calling).
GigaChat выбирает функцию → мы её вызываем → возвращаем результат.
"""
import json


# ========== ОПИСАНИЕ ФУНКЦИЙ ДЛЯ GIGACHAT ==========
FUNCTIONS_SCHEMA = [
    {
        "name": "get_value",
        "description": "Получить значение показателя за конкретный год. Например: выручка за 2024 год.",
        "parameters": {
            "type": "object",
            "properties": {
                "metric": {
                    "type": "string",
                    "description": "Название показателя, например 'Выручка' или 'Чистая прибыль'"
                },
                "year": {
                    "type": "integer",
                    "description": "Год, например 2024"
                }
            },
            "required": ["metric", "year"]
        }
    },
    {
        "name": "compare_years",
        "description": "Сравнить показатель между двумя годами: разница и процент изменения. Используй для вопросов вроде 'на сколько выросла/упала выручка'.",
        "parameters": {
            "type": "object",
            "properties": {
                "metric": {"type": "string", "description": "Название показателя"},
                "year1": {"type": "integer", "description": "Первый (старый) год"},
                "year2": {"type": "integer", "description": "Второй (новый) год"}
            },
            "required": ["metric", "year1", "year2"]
        }
    },
    {
        "name": "get_series",
        "description": "Получить временной ряд показателя по всем годам. Используй, когда спрашивают 'как менялась выручка по годам' или нужны данные для графика.",
        "parameters": {
            "type": "object",
            "properties": {
                "metric": {"type": "string", "description": "Название показателя"}
            },
            "required": ["metric"]
        }
    },
    {
        "name": "find_metrics",
        "description": "Найти показатели по части названия. Используй, если не уверен, как точно называется показатель. Например, 'прибыль' найдёт 'Чистая прибыль', 'Валовая прибыль', 'Прибыль от продаж'.",
        "parameters": {
            "type": "object",
            "properties": {
                "name_part": {"type": "string", "description": "Часть названия показателя"}
            },
            "required": ["name_part"]
        }
    },
    {
        "name": "list_metrics",
        "description": "Показать список ВСЕХ показателей в таблице. Используй, если пользователь спрашивает 'какие показатели есть?' или ты не знаешь, что есть в таблице.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "list_years",
        "description": "Показать список всех годов, за которые есть данные.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "top_metrics_for_year",
        "description": "Топ-N показателей за год по абсолютному значению. Используй для вопросов вроде 'какие самые крупные показатели за 2024 год'.",
        "parameters": {
            "type": "object",
            "properties": {
                "year": {"type": "integer", "description": "Год"},
                "limit": {"type": "integer", "description": "Сколько показателей вернуть (по умолчанию 5)"}
            },
            "required": ["year"]
        }
    },
    {
        "name": "find_max_year",
        "description": "Найти год с максимальным значением показателя. Например, 'в каком году выручка была максимальной?'",
        "parameters": {
            "type": "object",
            "properties": {
                "metric": {"type": "string", "description": "Название показателя"}
            },
            "required": ["metric"]
        }
    },
    {
        "name": "find_min_year",
        "description": "Найти год с минимальным значением показателя.",
        "parameters": {
            "type": "object",
            "properties": {
                "metric": {"type": "string", "description": "Название показателя"}
            },
            "required": ["metric"]
        }
    },
    {
        "name": "get_all_for_year",
        "description": "Показать все показатели за конкретный год.",
        "parameters": {
            "type": "object",
            "properties": {
                "year": {"type": "integer", "description": "Год"}
            },
            "required": ["year"]
        }
    }
]


def call_function(name, arguments, analytics_obj):
    """
    Вызывает нужную функцию из analytics.py по имени.
    name: название функции от GigaChat
    arguments: dict с аргументами
    analytics_obj: объект Analytics
    """
    try:
        if name == "get_value":
            result = analytics_obj.get_value(arguments['metric'], arguments['year'])

        elif name == "compare_years":
            result = analytics_obj.compare_years(
                arguments['metric'],
                arguments['year1'],
                arguments['year2']
            )

        elif name == "get_series":
            result = analytics_obj.get_series(arguments['metric'])

        elif name == "find_metrics":
            result = analytics_obj.find_metrics(arguments['name_part'])

        elif name == "list_metrics":
            result = analytics_obj.list_metrics()

        elif name == "list_years":
            result = analytics_obj.list_years()

        elif name == "top_metrics_for_year":
            limit = arguments.get('limit', 5)
            result = analytics_obj.top_metrics_for_year(arguments['year'], limit)

        elif name == "find_max_year":
            result = analytics_obj.find_max_year(arguments['metric'])

        elif name == "find_min_year":
            result = analytics_obj.find_min_year(arguments['metric'])

        elif name == "get_all_for_year":
            result = analytics_obj.get_all_for_year(arguments['year'])

        else:
            result = {"error": f"Функция '{name}' не найдена"}

        return result
    except Exception as e:
        return {"error": f"Ошибка вызова функции '{name}': {e}"}


if __name__ == '__main__':
    print("Модуль bot_functions.py готов.")
    print(f"Доступно функций: {len(FUNCTIONS_SCHEMA)}")
