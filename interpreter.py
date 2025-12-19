# interpreter.py: Интерпретатор УВМ

import json
import struct
import argparse
import sys
from uvmspec import UVMSpec24  # Импортируем спецификацию


class Interpreter:
    def __init__(self, memory_size=65536):  # Объединённая память, как в требованиях
        # Объединённая память для данных и кода
        self.memory = [0] * memory_size
        # Регистры
        self.registers = [0] * 8
        self.pc = 0  # Program Counter
        self.running = False
        self.spec = UVMSpec24()  # Используем спецификацию из uvmspec.py

    def load_program(self, binary_file_path):
        """Загружает бинарный файл программы."""
        with open(binary_file_path, 'rb') as f:
            self.program_data = f.read()
        self.pc = 0  # Сбросить PC при загрузке новой программы
        print(f"Программа загружена. Размер: {len(self.program_data)} байт.", file=sys.stderr)

    def decode_command(self, offset):
        """Декодирует одну команду из бинарных данных по смещению."""
        # Сначала читаем байт A
        opcode = self.program_data[offset]

        if opcode not in self.spec.CMD_SIZES:
            raise ValueError(f"Неизвестный код операции: {opcode}")

        size = self.spec.CMD_SIZES[opcode]
        raw_bytes = self.program_data[offset: offset + size]

        if len(raw_bytes) < size:
            raise ValueError(
                f"Недостаточно байт для декодирования команды {opcode} начиная с {offset}. Ожидается {size}, доступно {len(raw_bytes)}.")

        fields = {"A": opcode}
        field_info_list = self.spec.FIELDS.get(opcode, [])

        # Собираем все биты команды в один целочисленный объект
        command_bits = 0
        for i, byte_val in enumerate(raw_bytes):
            command_bits |= byte_val << (i * 8)

        for field_name, start_bit, end_bit in field_info_list:
            if field_name == "A":
                continue  # Уже прочитан
            mask_len = end_bit - start_bit + 1
            mask = (1 << mask_len) - 1
            value = (command_bits >> start_bit) & mask
            fields[field_name] = value

        return fields, size

    def fetch_decode_execute_cycle(self):
        """Выполняет один цикл выборки-декодирования-исполнения."""
        if self.pc >= len(self.program_data):
            self.running = False
            return

        # 1. Fetch: Получаем команду
        current_pc_before_cmd = self.pc
        try:
            command_fields, cmd_size = self.decode_command(self.pc)
        except ValueError as e:
            print(f"Ошибка декодирования команды на PC={self.pc}: {e}", file=sys.stderr)
            self.running = False
            return

        self.pc += cmd_size
        print(f"PC={current_pc_before_cmd}, Команда: {command_fields}, Размер: {cmd_size}", file=sys.stderr)

        # 2. Decode & Execute: Исполняем команду
        opcode = command_fields["A"]
        if opcode == self.spec.OP_LOAD:
            reg_addr = command_fields["B"]
            const_val = command_fields["C"]
            # Знаковая интерпретация 13-битного числа
            if const_val & (1 << 12):  # Если установлен 12-й бит (знаковый)
                const_val = const_val - (1 << 13)
            self.registers[reg_addr] = const_val
            print(f"  LOAD_CONST R{reg_addr} <- {const_val} (R={self.registers[reg_addr]})", file=sys.stderr)

        elif opcode == self.spec.OP_READ:
            offset = command_fields["B"]
            base_reg_addr = command_fields["D"]
            dest_reg_addr = command_fields["C"]

            # Знаковая интерпретация 13-битного смещения
            if offset & (1 << 12):
                offset = offset - (1 << 13)

            base_address = self.registers[base_reg_addr]
            effective_address = base_address + offset
            if 0 <= effective_address < len(self.memory):
                self.registers[dest_reg_addr] = self.memory[effective_address]
            else:
                print(f"  ОШИБКА: Выход за границы памяти при READ по адресу {effective_address}", file=sys.stderr)
                self.running = False
                return
            print(
                f"  READ_MEM M[R{base_reg_addr}+{offset}] -> R{dest_reg_addr} (M[{effective_address}]={self.registers[dest_reg_addr]})",
                file=sys.stderr)

        elif opcode == self.spec.OP_WRITE:
            src_reg_addr = command_fields["B"]
            addr_reg_addr = command_fields["C"]
            value_to_write = self.registers[src_reg_addr]
            address_to_write = self.registers[addr_reg_addr]
            if 0 <= address_to_write < len(self.memory):
                self.memory[address_to_write] = value_to_write
            else:
                print(f"  ОШИБКА: Выход за границы памяти при WRITE по адресу {address_to_write}", file=sys.stderr)
                self.running = False
                return
            print(f"  WRITE_MEM R{src_reg_addr}(={value_to_write}) -> M[R{addr_reg_addr}](={address_to_write})",
                  file=sys.stderr)

        elif opcode == self.spec.OP_SHIFT_RIGHT:
            val_reg_addr = command_fields["B"]
            shift_reg_addr = command_fields["C"]
            shift_offset = command_fields["D"]
            base_reg_addr = command_fields["E"]

            # Знаковая интерпретация 13-битного смещения
            if shift_offset & (1 << 12):
                shift_offset = shift_offset - (1 << 13)

            # Вычисляем сдвиг
            shift_amount = self.registers[shift_reg_addr] + shift_offset
            base_address = self.registers[base_reg_addr]

            # Значение для сдвига
            value_to_shift = self.registers[val_reg_addr]

            # Логический сдвиг вправо
            if shift_amount >= 32:
                shifted_value = 0
            elif shift_amount < 0:
                # Не определено поведение для отрицательного сдвига, установим в 0
                shifted_value = 0
                print(f"  ПРЕДУПРЕЖДЕНИЕ: Отрицательный сдвиг {shift_amount}, устанавливаем 0", file=sys.stderr)
            else:
                shifted_value = (value_to_shift & 0xFFFFFFFF) >> shift_amount

            # Записываем результат в память по вычисленному адресу
            effective_address = base_address
            if 0 <= effective_address < len(self.memory):
                self.memory[effective_address] = shifted_value
            else:
                print(f"  ОШИБКА: Выход за границы памяти при SHIFT_RIGHT по адресу {effective_address}",
                      file=sys.stderr)
                self.running = False
                return

            print(
                f"  SHIFT_RIGHT R{val_reg_addr}(={value_to_shift}) >> {shift_amount} -> M[R{base_reg_addr}](={effective_address}), Val={shifted_value}",
                file=sys.stderr)

        else:
            print(f"Неизвестная команда: {opcode}", file=sys.stderr)
            self.running = False

    def run(self, trace=False):
        """Запускает выполнение программы."""
        self.running = True
        step = 0
        while self.running:
            if trace:
                print(f"--- Шаг {step} ---", file=sys.stderr)
            self.fetch_decode_execute_cycle()
            step += 1
            # Защита от бесконечного цикла в случае ошибки декодирования
            if step > 10000:
                print("Достигнут лимит шагов (10000), возможно зацикливание.", file=sys.stderr)
                break
        print(f"Выполнение завершено за {step} шагов.", file=sys.stderr)

    def dump_memory(self, output_file, start_addr=0, end_addr=None):
        """Сохраняет дамп памяти в файл (JSON)."""
        if end_addr is None:
            end_addr = len(self.memory)
        end_addr = min(end_addr, len(self.memory))

        # Формат дампа: список значений
        dump_data = self.memory[start_addr:end_addr]

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(dump_data, f, indent=2)
        print(f"Дамп памяти (адреса {start_addr}-{end_addr - 1}) сохранен в {output_file}")


def main():
    parser = argparse.ArgumentParser(description='Интерпретатор УВМ (вариант 24) - Использует мнемоники')
    parser.add_argument('--input', required=True, help='Входной бинарный файл')
    parser.add_argument('--output', required=True, help='Выходной файл дампа памяти (JSON)')
    parser.add_argument('--range', type=str, help='Диапазон адресов памяти для дампа (например, "0-100")')
    parser.add_argument('--trace', action='store_true', help='Включить трассировку выполнения')

    args = parser.parse_args()

    interp = Interpreter()

    try:
        interp.load_program(args.input)
        interp.run(trace=args.trace)

        start_addr, end_addr = 0, None
        if args.range:
            try:
                range_parts = args.range.split('-')
                if len(range_parts) == 2:
                    start_addr = int(range_parts[0])
                    end_addr = int(range_parts[1]) + 1  # Включительно
                else:
                    raise ValueError
            except (ValueError, IndexError):
                print(f"Неверный формат диапазона: {args.range}. Ожидается 'start-end'.", file=sys.stderr)
                return

        interp.dump_memory(args.output, start_addr, end_addr)

    except FileNotFoundError:
        print(f"Ошибка: Файл {args.input} не найден.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Ошибка интерпретации: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()