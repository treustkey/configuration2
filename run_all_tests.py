import subprocess
import sys
import os

def run_test(assembler_path, interpreter_path, test_csv_path):
    """Запускает один тест: ассемблирует и интерпретирует."""
    print(f"--- Тестируем файл: {test_csv_path} ---")

    # Генерируем имена файлов
    base_name = os.path.splitext(os.path.basename(test_csv_path))[0]
    binary_file = f"tests/{base_name}.bin"
    output_log = f"tests/{base_name}_output.log"
    memory_dump = f"tests/{base_name}_memory_dump.mem"

    # 1. Ассемблирование
    print("1. Ассемблирование...")
    try:
        result_asm = subprocess.run([
            sys.executable, assembler_path, '--input', test_csv_path, '--output', binary_file, '--test'
        ], capture_output=True, text=True, check=True)
        print(result_asm.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Ошибка ассемблирования для {test_csv_path}: {e.stderr}")
        return False

    # 2. Интерпретация
    print("2. Интерпретация...")
    try:
        with open(output_log, 'w') as log_f:
            result_interp = subprocess.run([
                sys.executable, interpreter_path, '--input', binary_file, '--output', memory_dump, '--trace'
            ], stdout=log_f, stderr=subprocess.STDOUT, check=True)
        print(f"  Вывод интерпретатора сохранен в {output_log}")
        print(f"  Дамп памяти сохранен в {memory_dump}")
    except subprocess.CalledProcessError as e:
        print(f"Ошибка интерпретации для {binary_file}")
        # Пишем ошибку в лог, даже если интерпретация упала
        with open(output_log, 'a') as log_f:
            log_f.write(f"\n--- ОШИБКА ИНТЕРПРЕТАЦИИ ---\n{e}\n")
        return False

    print(f"3. Бинарный файл сохранен в {binary_file}")
    print("")
    return True

def run_all_tests(assembler_path, interpreter_path, tests_dir="tests"):
    """Находит и запускает все тесты в директории."""
    if not os.path.isfile(assembler_path):
        print(f"Ошибка: Ассемблер '{assembler_path}' не найден.")
        return
    if not os.path.isfile(interpreter_path):
        print(f"Ошибка: Интерпретатор '{interpreter_path}' не найден.")
        return

    success_count = 0
    total_count = 0

    for filename in os.listdir(tests_dir):
        if filename.startswith("test_example_") and filename.endswith(".csv"):
            test_path = os.path.join(tests_dir, filename)
            total_count += 1
            if run_test(assembler_path, interpreter_path, test_path):
                success_count += 1

    print(f"--- Сводка ---")
    print(f"Всего тестов: {total_count}")
    print(f"Успешно пройдено: {success_count}")
    print(f"Провалено: {total_count - success_count}")


if __name__ == "__main__":
    # Пути к ассемблеру и интерпретатору (предполагаем, что они находятся в корне репозитория)
    ASSEMBLER_PATH = "assembler.py"  # или путь к исполняемому файлу
    INTERPRETER_PATH = "interpreter.py"  # или путь к исполняемому файлу

    if len(sys.argv) == 3:
        ASSEMBLER_PATH = sys.argv[1]
        INTERPRETER_PATH = sys.argv[2]

    run_all_tests(ASSEMBLER_PATH, INTERPRETER_PATH)