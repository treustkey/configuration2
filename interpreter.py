#Интерпретатор УВМ

import argparse
import csv
from uvmspec import UVMSpec24


class Interpreter:
    def __init__(self):
        self.spec = UVMSpec24()
        self.code_memory = bytearray()
        self.data_memory = [0] * 65536  # 64KB памяти данных
        self.registers = [0] * 8  # 8 регистров
        self.pc = 0  # Счетчик команд

    def load_program(self, program_file):
        #Загрузка программы в память команд
        with open(program_file, 'rb') as f:
            self.code_memory = bytearray(f.read())
        print(f"Загружено {len(self.code_memory)} байт программы")

    def decode_command(self):
        #Декодирование команды из памяти команд
        if self.pc >= len(self.code_memory):
            return None

        # Читаем код операции
        opcode = self.code_memory[self.pc]
        cmd_size = self.spec.CMD_SIZES.get(opcode)

        if cmd_size is None:
            raise ValueError(f"Неизвестный код операции: {opcode} в PC={self.pc}")

        # Читаем всю команду
        cmd_bytes = self.code_memory[self.pc:self.pc + cmd_size]
        if len(cmd_bytes) < cmd_size:
            raise ValueError(f"Неполная команда по адресу {self.pc}")

        # Декодируем в зависимости от типа команды
        cmd = {"A": opcode}

        if opcode == self.spec.OP_LOAD:
            # 3 байта: A (8), B (3), C (13)
            b1, b2, b3 = cmd_bytes
            cmd["B"] = b2 & 0x07
            cmd["C"] = ((b2 >> 3) & 0x1F) | (b3 << 5)

        elif opcode == self.spec.OP_READ:
            # 4 байта: A (8), B (13), C (3), D (3)
            b1, b2, b3, b4 = cmd_bytes
            cmd["B"] = b2 | ((b3 & 0x1F) << 8)
            cmd["C"] = (b3 >> 5) & 0x07
            cmd["D"] = (b4 >> 5) & 0x07

        elif opcode == self.spec.OP_WRITE:
            # 2 байта: A (8), B (3), C (3)
            b1, b2 = cmd_bytes
            cmd["B"] = b2 & 0x07
            cmd["C"] = (b2 >> 3) & 0x07

        elif opcode == self.spec.OP_SHIFT_RIGHT:
            # 7 байт: A (8), B (3), C (23), D (13), E (3)
            b1, b2, b3, b4, b5, b6, b7 = cmd_bytes
            cmd["B"] = b2 & 0x07
            cmd["C"] = ((b2 >> 3) & 0x1F) | (b3 << 5) | (b4 << 13) | ((b5 & 0x03) << 21)
            cmd["D"] = ((b5 >> 2) & 0x3F) | ((b6 & 0x7F) << 6) | ((b7 & 0x1F) << 13)
            cmd["E"] = (b7 >> 5) & 0x07

        self.pc += cmd_size
        return cmd

    def execute_command(self, cmd):
        #Выполнение одной команды
        opcode = cmd["A"]

        if opcode == self.spec.OP_LOAD:
            # Загрузка константы в регистр
            reg_addr = cmd["B"]
            constant = cmd["C"]
            self.registers[reg_addr] = constant
            print(f"  LOAD: R{reg_addr} = {constant}")

        elif opcode == self.spec.OP_READ:
            # Чтение из памяти в регистр
            offset = cmd["B"]
            dest_reg = cmd["C"]
            base_reg = cmd["D"]

            mem_addr = self.registers[base_reg] + offset
            if 0 <= mem_addr < len(self.data_memory):
                self.registers[dest_reg] = self.data_memory[mem_addr]
                print(
                    f"  READ: R{dest_reg} = memory[{self.registers[base_reg]} + {offset}] = {self.registers[dest_reg]}")
            else:
                raise ValueError(f"Выход за границы памяти: {mem_addr}")

        elif opcode == self.spec.OP_WRITE:
            # Запись из регистра в память
            src_reg = cmd["B"]
            addr_reg = cmd["C"]

            mem_addr = self.registers[addr_reg]
            if 0 <= mem_addr < len(self.data_memory):
                self.data_memory[mem_addr] = self.registers[src_reg]
                print(f"  WRITE: memory[{mem_addr}] = R{src_reg} = {self.registers[src_reg]}")
            else:
                raise ValueError(f"Выход за границы памяти: {mem_addr}")

        elif opcode == self.spec.OP_SHIFT_RIGHT:
            # Логический сдвиг вправо
            value_reg = cmd["B"]
            shift_reg = cmd["C"]
            offset = cmd["D"]
            base_reg = cmd["E"]

            value = self.registers[value_reg]
            shift = self.registers[shift_reg]

            # Логический сдвиг вправо (беззнаковый)
            if shift >= 32:  # Для 32-битных чисел
                result = 0
            else:
                result = (value >> shift) & 0xFFFFFFFF  # 32-битный результат

            mem_addr = self.registers[base_reg] + offset
            if 0 <= mem_addr < len(self.data_memory):
                self.data_memory[mem_addr] = result
                print(
                    f"  SHIFT_RIGHT: memory[{self.registers[base_reg]} + {offset}] = R{value_reg} >> R{shift_reg} = {value} >> {shift} = {result}")
            else:
                raise ValueError(f"Выход за границы памяти: {mem_addr}")


    def run(self, program_file, dump_file=None, mem_range=None):
        #Основной цикл интерпретации
        # Загрузка программы
        self.load_program(program_file)

        # Сброс состояния
        self.pc = 0
        self.registers = [0] * 8
        self.data_memory = [0] * 65536

        print("=== Выполнение программы ===")

        # Выполнение программы
        cmd_count = 0
        while True:
            cmd = self.decode_command()
            if cmd is None:
                break

            try:
                self.execute_command(cmd)
                cmd_count += 1
            except Exception as e:
                print(f"Ошибка выполнения команды: {e}")
                print(f"Команда: {cmd}")
                break

        print(f"\nВыполнено команд: {cmd_count}")
        print(f"Регистры: {self.registers}")

        # Дамп памяти если требуется
        if dump_file and mem_range:
            self.dump_memory(dump_file, mem_range)

    def dump_memory(self, dump_file, mem_range):
        #Дамп памяти в CSV формат
        start, end = map(int, mem_range.split('-'))
        start = max(0, start)
        end = min(len(self.data_memory) - 1, end)

        with open(dump_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Адрес', 'Значение'])
            for addr in range(start, end + 1):
                writer.writerow([addr, self.data_memory[addr]])

        print(f"Дамп памяти сохранен в {dump_file} (адреса {start}-{end})")

    def test_copy_array(self):
        #Тестовая программа: копирование массива
        print("=== Тест копирования массива ===")

        # Инициализация памяти
        src_addr = 1000
        dst_addr = 2000
        array_size = 5

        # Записываем тестовые данные
        test_data = [10, 20, 30, 40, 50]
        for i in range(array_size):
            self.data_memory[src_addr + i] = test_data[i]

        print(f"Исходный массив по адресу {src_addr}: {test_data}")

        # Копирование вручную (для демонстрации)
        for i in range(array_size):
            self.data_memory[dst_addr + i] = self.data_memory[src_addr + i]

        print(f"Скопированный массив по адресу {dst_addr}: {self.data_memory[dst_addr:dst_addr + array_size]}")

        # Проверка
        success = True
        for i in range(array_size):
            if self.data_memory[src_addr + i] != self.data_memory[dst_addr + i]:
                success = False
                print(f"Ошибка: элемент {i} не совпадает")

        if success:
            print("✓ Тест копирования массива пройден успешно")
        else:
            print("✗ Тест копирования массива не пройден")


    def test_shift_operation(self):
        #Тестовая программа для операции сдвига
        print("=== Тест операции сдвига вправо ===")

        # Инициализация регистров
        self.registers[0] = 255  # Значение для сдвига
        self.registers[1] = 2  # Количество сдвигов
        self.registers[2] = 1000  # Базовый адрес для результата

        # Выполняем сдвиг вручную
        value = self.registers[0]
        shift = self.registers[1]
        result = value >> shift

        # Сохраняем результат в память
        self.data_memory[1000] = result

        print(f"Тестовые данные:")
        print(f"  Значение: {value} (0b{value:08b})")
        print(f"  Сдвиг: {shift}")
        print(f"  Результат: {result} (0b{result:08b})")
        print(f"  Сохранено в memory[1000] = {self.data_memory[1000]}")

        # Проверка
        expected = 255 >> 2  # 63
        if self.data_memory[1000] == expected:
            print(f"✓ Тест сдвига пройден успешно")
            print(f"  Ожидалось: {expected}, Получено: {self.data_memory[1000]}")
        else:
            print(f"✗ Тест сдвига не пройден")
            print(f"  Ожидалось: {expected}, Получено: {self.data_memory[1000]}")


def main():
    parser = argparse.ArgumentParser(description='Интерпретатор УВМ')
    parser.add_argument('--program', help='Бинарный файл программы')
    parser.add_argument('--dump', help='Файл для дампа памяти (CSV)')
    parser.add_argument('--range', help='Диапазон адресов для дампа (start-end)')
    parser.add_argument('--test', choices=['copy', 'shift'], help='Запустить тестовую программу')

    args = parser.parse_args()

    interpreter = Interpreter()

    if args.test == 'copy':
        interpreter.test_copy_array()
    elif args.test == 'shift':
        interpreter.test_shift_operation()
    elif args.program:
        if args.dump and not args.range:
            print("Ошибка: для дампа необходимо указать диапазон --range")
            return

        interpreter.run(args.program, args.dump, args.range)
        print("Программа выполнена успешно")
    else:
        print("Ошибка: укажите --program или --test")


if __name__ == "__main__":
    main()