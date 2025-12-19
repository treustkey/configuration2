# assembler.py: Ассемблер УВМ

import argparse
import csv
from pathlib import Path
from uvmspec import UVMSpec24


class Assembler:
    def __init__(self):
        self.spec = UVMSpec24()
        self.commands = []
        self.mnemonic_to_opcode = {
            "LOAD_CONST": self.spec.OP_LOAD,
            "READ_MEM": self.spec.OP_READ,
            "WRITE_MEM": self.spec.OP_WRITE,
            "SHIFT_RIGHT": self.spec.OP_SHIFT_RIGHT,
        }
        # Словарь для сопоставления числовых кодов мнемоникам (для обратного преобразования, если нужно)
        self.opcode_to_mnemonic = {v: k for k, v in self.mnemonic_to_opcode.items()}

    def parse_csv(self, input_file):
        """Парсинг CSV файла в промежуточное представление, ожидая мнемоники."""
        self.commands = []

        with open(input_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row_num, row in enumerate(reader, 1):
                # Пропускаем пустые строки и комментарии
                if not row or row[0].strip().startswith('#'):
                    continue

                # Очищаем значения
                values = [v.strip() for v in row]

                if not values:
                    continue # Защита от строки с только комментарием или пробелами

                # Определяем команду по мнемонике
                mnemonic = values[0]
                if mnemonic not in self.mnemonic_to_opcode:
                    raise ValueError(f"Неизвестная мнемоника в строке {row_num}: {mnemonic}")

                opcode = self.mnemonic_to_opcode[mnemonic]

                # Создаем словарь с полями, включая числовую команду
                cmd = {"A": opcode, "mnemonic": mnemonic} # Добавляем мнемонику для прозрачности

                # Заполняем остальные поля в зависимости от кода операции
                # Здесь важна проверка по opcode, так как spec знает о форматах
                if opcode == self.spec.OP_LOAD:
                    if len(values) >= 3:
                        cmd["B"] = int(values[1])  # Адрес регистра
                        cmd["C"] = int(values[2])  # Константа
                    else:
                        raise ValueError(f"Недостаточно аргументов для команды {mnemonic} в строке {row_num}")
                elif opcode == self.spec.OP_READ:
                    if len(values) >= 4:
                        cmd["B"] = int(values[1])  # Смещение
                        cmd["C"] = int(values[2])  # Адрес регистра (результат)
                        cmd["D"] = int(values[3])  # Адрес регистра (база)
                    else:
                        raise ValueError(f"Недостаточно аргументов для команды {mnemonic} в строке {row_num}")
                elif opcode == self.spec.OP_WRITE:
                    if len(values) >= 3:
                        cmd["B"] = int(values[1])  # Адрес регистра (данные)
                        cmd["C"] = int(values[2])  # Адрес регистра (адрес)
                    else:
                        raise ValueError(f"Недостаточно аргументов для команды {mnemonic} в строке {row_num}")
                elif opcode == self.spec.OP_SHIFT_RIGHT:
                    if len(values) >= 5:
                        cmd["B"] = int(values[1])  # Адрес регистра (значение)
                        cmd["C"] = int(values[2])  # Адрес регистра (сдвиг)
                        cmd["D"] = int(values[3])  # Смещение
                        cmd["E"] = int(values[4])  # Адрес регистра (база)
                    else:
                        raise ValueError(f"Недостаточно аргументов для команды {mnemonic} в строке {row_num}")
                else:
                    # Эта проверка теперь технически лишняя, так как мы уже проверили мнемонику,
                    # но пусть будет для безопасности.
                    raise ValueError(f"Неизвестный код операции в строке {row_num}: {opcode}")

                self.commands.append(cmd)

        return self.commands

    def assemble(self, input_file, output_file=None, test_mode=False):
        """Основная функция ассемблирования"""
        # Парсинг CSV
        commands = self.parse_csv(input_file)

        # Генерация бинарного кода
        binary_data = bytearray()
        for cmd in commands:
            # Передаём в encode_command словарь с числовыми полями A, B, C...
            # Функция encode_command в UVMSpec24 должна использовать числовые значения полей
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
                # Убираем служебное поле 'mnemonic' из вывода, если оно было добавлено только для отладки
                # или оставляем его для наглядности
                cmd_for_print = {k: v for k, v in cmd.items() if k != 'mnemonic'} # Опционально
                # print(f"Команда {i}: {cmd}") # <-- Если хотим видеть мнемонику
                print(f"Команда {i}: {cmd_for_print}") # <-- Если выводим как раньше, без мнемоники

            print(f"\n=== Бинарный код ({len(binary_data)} байт) ===")
            for i, byte in enumerate(binary_data):
                print(f"0x{byte:02X}", end=", " if (i + 1) % 8 != 0 else "\n")
            if len(binary_data) % 8 != 0:
                print()

            # Сравнение с тестовыми командами
            print(f"\n=== Проверка тестовых команд ===")
            for test_name, test_data in self.spec.TEST_COMMANDS.items():
                print(f"\n{test_name.upper()}:")
                # Предполагаем, что TEST_COMMANDS теперь содержит числовые коды
                # и что encode_command ожидает числовые поля
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
    parser = argparse.ArgumentParser(description='Ассемблер УВМ (вариант 24) - Использует мнемоники')
    parser.add_argument('--input', required=True, help='Входной CSV файл с мнемониками')
    parser.add_argument('--output', help='Выходной бинарный файл')
    parser.add_argument('--test', action='store_true', help='Режим тестирования')

    args = parser.parse_args()

    assembler = Assembler()
    assembler.assemble(args.input, args.output, args.test)


if __name__ == "__main__":
    main()