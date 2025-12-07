#Ассемблер УВМ

import argparse
import csv
from pathlib import Path
from uvmspec import UVMSpec24


class Assembler:
    def __init__(self):
        self.spec = UVMSpec24()
        self.commands = []

    def parse_csv(self, input_file):
        #Парсинг CSV файла в промежуточное представление
        self.commands = []

        with open(input_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row_num, row in enumerate(reader, 1):
                # Пропускаем пустые строки и комментарии
                if not row or row[0].strip().startswith('#'):
                    continue

                # Очищаем значения
                values = [v.strip() for v in row]

                # Определяем команду по коду операции
                try:
                    opcode = int(values[0])
                except ValueError:
                    raise ValueError(f"Неверный код операции в строке {row_num}: {values[0]}")

                # Создаем словарь с полями
                cmd = {"A": opcode}

                # Заполняем остальные поля
                if opcode == self.spec.OP_LOAD:
                    if len(values) >= 3:
                        cmd["B"] = int(values[1])  # Адрес регистра
                        cmd["C"] = int(values[2])  # Константа
                elif opcode == self.spec.OP_READ:
                    if len(values) >= 4:
                        cmd["B"] = int(values[1])  # Смещение
                        cmd["C"] = int(values[2])  # Адрес регистра (результат)
                        cmd["D"] = int(values[3])  # Адрес регистра (база)
                elif opcode == self.spec.OP_WRITE:
                    if len(values) >= 3:
                        cmd["B"] = int(values[1])  # Адрес регистра (данные)
                        cmd["C"] = int(values[2])  # Адрес регистра (адрес)
                elif opcode == self.spec.OP_SHIFT_RIGHT:
                    if len(values) >= 5:
                        cmd["B"] = int(values[1])  # Адрес регистра (значение)
                        cmd["C"] = int(values[2])  # Адрес регистра (сдвиг)
                        cmd["D"] = int(values[3])  # Смещение
                        cmd["E"] = int(values[4])  # Адрес регистра (база)
                else:
                    raise ValueError(f"Неизвестный код операции в строке {row_num}: {opcode}")

                self.commands.append(cmd)

        return self.commands

    def assemble(self, input_file, output_file=None, test_mode=False):
        #Основная функция ассемблирования
        # Парсинг CSV
        commands = self.parse_csv(input_file)

        # Генерация бинарного кода
        binary_data = bytearray()
        for cmd in commands:
            binary_data.extend(self.spec.encode_command(cmd))

        # Запись в файл (если указан)
        if output_file:
            with open(output_file, 'wb') as f:
                f.write(binary_data)
            print(f"Бинарный файл сохранен: {output_file}")

        # Вывод информации
        if test_mode:
            print("=== Промежуточное представление ===")
            for i, cmd in enumerate(commands):
                print(f"Команда {i}: {cmd}")

            print(f"\n=== Бинарный код ({len(binary_data)} байт) ===")
            for i, byte in enumerate(binary_data):
                print(f"0x{byte:02X}", end=", " if (i + 1) % 8 != 0 else "\n")
            if len(binary_data) % 8 != 0:
                print()

            # Сравнение с тестовыми командами
            print(f"\n=== Проверка тестовых команд ===")
            for test_name, test_data in self.spec.TEST_COMMANDS.items():
                print(f"\n{test_name.upper()}:")
                encoded = self.spec.encode_command(test_data["fields"])
                expected = bytes(test_data["hex"])
                if encoded == expected:
                    print(f"  ✓ Кодирование корректно")
                    print(f"  Байты: {', '.join(f'0x{b:02X}' for b in encoded)}")
                else:
                    print(f"  ✗ Ошибка кодирования")
                    print(f"  Ожидалось: {', '.join(f'0x{b:02X}' for b in expected)}")
                    print(f"  Получено:  {', '.join(f'0x{b:02X}' for b in encoded)}")

        print(f"Ассемблировано команд: {len(commands)}")
        print(f"Размер бинарного кода: {len(binary_data)} байт")

        return commands, binary_data

def main():
    parser = argparse.ArgumentParser(description='Ассемблер УВМ (вариант 24) - Этап 2')
    parser.add_argument('--input', required=True, help='Входной CSV файл')
    parser.add_argument('--output', help='Выходной бинарный файл')
    parser.add_argument('--test', action='store_true', help='Режим тестирования')

    args = parser.parse_args()

    assembler = Assembler()
    assembler.assemble(args.input, args.output, args.test)


if __name__ == "__main__":
    main()