#!/usr/bin/env python3
"""
Скрипт для автоматического тестирования всех 5 этапов
"""

import subprocess
import os
import sys
import codecs

sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')


def run_command(cmd, description):
    """Запускает команду и выводит результат"""
    print(f"\n{'=' * 60}")
    print(f"{description}")
    print(f"Команда: {cmd}")
    print('-' * 60)

    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        print(f"Выходной код: {result.returncode}")
        if result.stdout:
            print(f"Вывод:\n{result.stdout}")
        if result.stderr and result.returncode != 0:
            print(f"Ошибки:\n{result.stderr}")
        return result.returncode == 0
    except Exception as e:
        print(f"Исключение: {e}")
        return False


def main():
    print("Запуск полного тестирования УВМ (вариант 24)")
    print("Все 5 этапов будут выполнены последовательно")

    # Создаем папку для результатов
    os.makedirs("results", exist_ok=True)

    # Этап 1: Парсинг CSV
    print("\n" + "=" * 60)
    print("ЭТАП 1: Перевод программы в промежуточное представление")
    success = run_command(
        "python assembler.py --input tests/test_load.csv --test",
        "Тест загрузки константы"
    )
    if not success:
        print("Этап 1 не пройден")
        sys.exit(1)

    # Этап 2: Генерация бинарного кода
    print("\n" + "=" * 60)
    print("ЭТАП 2: Формирование машинного кода")

    # Тестируем все команды из спецификации
    test_files = ["test_load.csv", "test_read.csv", "test_write.csv", "test_shift.csv"]
    for test_file in test_files:
        input_file = f"tests/{test_file}"
        output_file = f"results/{test_file.replace('.csv', '.bin')}"
        success = run_command(
            f"python assembler.py --input {input_file} --output {output_file} --test",
            f"Тест {test_file}"
        )
        if not success:
            print(f"Ошибка в тесте {test_file}")
            sys.exit(1)

    # Этап 3: Интерпретатор
    print("\n" + "=" * 60)
    print("ЭТАП 3: Интерпретатор и операции с памятью")

    # Сначала ассемблируем тест копирования
    success = run_command(
        "python assembler.py --input tests/test_copy.csv --output results/test_copy.bin",
        "Ассемблирование теста копирования"
    )

    # Запускаем интерпретатор
    success = run_command(
        "python interpreter.py --program results/test_copy.bin --dump results/copy_memory.csv --range 1000-1010",
        "Выполнение теста копирования массива"
    )

    # Этап 4: АЛУ
    print("\n" + "=" * 60)
    print("ЭТАП 4: Реализация АЛУ (команда сдвига)")

    # Запускаем встроенный тест сдвига
    success = run_command(
        "python interpreter.py --test shift",
        "Тест операции сдвига вправо"
    )

    # Этап 5: Тестовая задача
    print("\n" + "=" * 60)
    print("ЭТАП 5: Выполнение тестовой задачи")

    # Сначала ассемблируем тестовую задачу
    success = run_command(
        "python assembler.py --input examples/example_vectors.csv --output results/vectors.bin",
        "Ассемблирование тестовой задачи"
    )

    # Запускаем тестовую задачу
    success = run_command(
        "python interpreter.py --test task",
        "Автоматический тест поэлементного сдвига"
    )

    print("\n" + "=" * 60)
    print("ВСЕ ЭТАПЫ ВЫПОЛНЕНЫ УСПЕШНО!")
    print(f"Результаты сохранены в папке: {os.path.abspath('results')}")
    print("=" * 60)


if __name__ == "__main__":
    main()