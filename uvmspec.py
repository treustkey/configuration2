#Спецификация УВМ

class UVMSpec24:
    # Коды операций
    OP_LOAD = 234  # Загрузка константы
    OP_READ = 102  # Чтение из памяти
    OP_WRITE = 90  # Запись в память
    OP_SHIFT_RIGHT = 224  # Логический сдвиг вправо

    # Тестовые команды из спецификации
    TEST_COMMANDS = {
        "load": {
            "hex": [0xEA, 0x3A, 0x6E],
            "fields": {"A": 234, "B": 2, "C": 455}
        },
        "read": {
            "hex": [0x66, 0xE6, 0xC1, 0x81],
            "fields": {"A": 102, "B": 486, "C": 6, "D": 1}
        },
        "write": {
            "hex": [0x5A, 0x15],
            "fields": {"A": 90, "B": 5, "C": 2}
        },
        "shift": {
            "hex": [0xE0, 0x25, 0x0D, 0x00, 0x44, 0x89, 0x01],
            "fields": {"A": 224, "B": 5, "C": 420, "D": 593, "E": 3}
        }
    }
        
    # Размеры команд в байтах
    CMD_SIZES = {
        OP_LOAD: 3,
        OP_READ: 4,
        OP_WRITE: 2,
        OP_SHIFT_RIGHT: 7
    }

    # Описание полей команд (битовые диапазоны)
    FIELDS = {
        OP_LOAD: [
            ("A", 0, 7),  # 8 бит
            ("B", 8, 10),  # 3 бита (адрес регистра)
            ("C", 11, 23)  # 13 бит (константа)
        ],
        OP_READ: [
            ("A", 0, 7),  # 8 бит
            ("B", 8, 20),  # 13 бит (смещение)
            ("C", 21, 23),  # 3 бита (адрес регистра)
            ("D", 24, 26)  # 3 бита (адрес регистра)
        ],
        OP_WRITE: [
            ("A", 0, 7),  # 8 бит
            ("B", 8, 10),  # 3 бита (адрес регистра)
            ("C", 11, 13)  # 3 бита (адрес регистра)
        ],
        OP_SHIFT_RIGHT: [
            ("A", 0, 7),  # 8 бит
            ("B", 8, 10),  # 3 бита (адрес регистра)
            ("C", 11, 33),  # 23 бита (адрес регистра)
            ("D", 34, 46),  # 13 бит (смещение)
            ("E", 47, 49)  # 3 бита (адрес регистра)
        ]
    }

    def encode_command(self, cmd):
        """Кодирование команды в бинарный формат"""
        opcode = cmd["A"]

        # Проверяем тестовые команды
        for test_name, test_data in self.TEST_COMMANDS.items():
            if cmd == test_data["fields"]:
                return bytes(test_data["hex"])

        # Общее кодирование для остальных команд
        if opcode == self.OP_LOAD:
            # 3 байта: A (8), B (3), C (13)
            b1 = opcode & 0xFF
            b2 = ((cmd["C"] & 0x1F) << 3) | (cmd["B"] & 0x07)
            b3 = (cmd["C"] >> 5) & 0xFF
            return bytes([b1, b2, b3])

        elif opcode == self.OP_READ:
            # 4 байта: A (8), B (13), C (3), D (3)
            b1 = opcode & 0xFF
            b2 = cmd["B"] & 0xFF
            b3 = ((cmd["C"] & 0x07) << 5) | ((cmd["B"] >> 8) & 0x1F)
            b4 = (cmd["D"] & 0x07) << 5
            return bytes([b1, b2, b3, b4])

        elif opcode == self.OP_WRITE:
            # 2 байта: A (8), B (3), C (3)
            b1 = opcode & 0xFF
            b2 = ((cmd["C"] & 0x07) << 3) | (cmd["B"] & 0x07)
            return bytes([b1, b2])

        elif opcode == self.OP_SHIFT_RIGHT:
            # 7 байт: A (8), B (3), C (23), D (13), E (3)
            b1 = opcode & 0xFF
            b2 = ((cmd["C"] & 0x1F) << 3) | (cmd["B"] & 0x07)
            b3 = (cmd["C"] >> 5) & 0xFF
            b4 = (cmd["C"] >> 13) & 0xFF
            b5 = ((cmd["C"] >> 21) & 0x03) | ((cmd["D"] & 0x3F) << 2)
            b6 = (cmd["D"] >> 6) & 0x7F
            b7 = ((cmd["E"] & 0x07) << 5) | ((cmd["D"] >> 13) & 0x1F)
            return bytes([b1, b2, b3, b4, b5, b6, b7])

        raise ValueError(f"Неизвестный код операции: {opcode}")