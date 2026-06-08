import re
import sys
from dataclasses import dataclass


# Таблицы лексем
KEYWORDS = {'#include', 'int', 'bool', 'for', 'if', 'else', 'return'}
BOOL_CONSTANTS = {'true', 'false'}


# Класс токена: два поля (тип и лексема)
@dataclass
class Token:
    type: str
    value: str


# Спецификация токенов (порядок важен)
# Ошибочные шаблоны идут раньше корректных, чтобы перехватывать ошибки
TOKEN_SPEC = [
    ('PREPROC',       r'\#\s*include'),                 # директива #include
    ('STRING',        r'"(?:\\.|[^"\\\n])*"'),          # строковый литерал
    ('STRING_BAD',    r'"(?:\\.|[^"\\\n])*'),           # незакрытая строка
    ('NUMBER_BAD',    r'\d+\.\d*\.[\d.]*'),             # две точки подряд
    ('IDENT_BAD',     r'\d+[A-Za-z_]\w*'),              # буквы в числе или id с цифры
    ('FLOAT',         r'\d+\.\d+'),                     # вещественное число
    ('INT',           r'\d+'),                          # целое число
    ('IDENT',         r'[A-Za-z_]\w*'),                 # идентификатор или ключевое слово
    ('OPERATOR',      r'::|<<|>>|<=|>=|==|!=|&&|\|\||\+\+|--|\*=|\+=|-=|/=|[-+*/=<>]'),
    ('DELIMITER',     r'[(){};,]'),                     # разделители
    ('NEWLINE',       r'\n'),                           # перевод строки
    ('SKIP',          r'[ \t]+'),                       # пробелы и табы
    ('MISMATCH',      r'.'),                            # любой другой символ
]

MASTER_RE = re.compile('|'.join(f'(?P<{name}>{pat})' for name, pat in TOKEN_SPEC))


def tokenize(code):
    """Разбивает очищенный код на список токенов. Возвращает (tokens, errors)."""
    tokens = []
    errors = []
    line = 1

    for mo in MASTER_RE.finditer(code):
        kind = mo.lastgroup
        value = mo.group()

        if kind == 'NEWLINE':
            line += 1
        elif kind == 'SKIP':
            continue
        elif kind == 'PREPROC':
            tokens.append(Token('KEYWORD', '#include'))
        elif kind == 'STRING':
            tokens.append(Token('CONSTANT_STRING', value))
        elif kind == 'STRING_BAD':
            errors.append(f"Лексическая ошибка (строка {line}): "
                          f"незакрытый строковый литерал {value!r}")
        elif kind == 'NUMBER_BAD':
            errors.append(f"Лексическая ошибка (строка {line}): "
                          f"некорректное число '{value}' (две точки подряд)")
        elif kind == 'IDENT_BAD':
            errors.append(f"Лексическая ошибка (строка {line}): "
                          f"идентификатор не может начинаться с цифры '{value}'")
        elif kind == 'FLOAT':
            tokens.append(Token('CONSTANT_FLOAT', value))
        elif kind == 'INT':
            tokens.append(Token('CONSTANT_INT', value))
        elif kind == 'IDENT':
            if value in KEYWORDS:
                tokens.append(Token('KEYWORD', value))
            elif value in BOOL_CONSTANTS:
                tokens.append(Token('CONSTANT_BOOL', value))
            else:
                tokens.append(Token('IDENTIFIER', value))
        elif kind == 'OPERATOR':
            tokens.append(Token('OPERATOR', value))
        elif kind == 'DELIMITER':
            tokens.append(Token('DELIMITER', value))
        elif kind == 'MISMATCH':
            errors.append(f"Лексическая ошибка (строка {line}): "
                          f"недопустимый символ '{value}'")

    return tokens, errors


def print_lexeme_table(tokens):
    """Выводит таблицу лексем в виде «Лексема | Тип»."""
    print('Лексема'.ljust(22) + '| Тип')
    print('-' * 22 + '+' + '-' * 20)
    for t in tokens:
        print(t.value.ljust(22) + '| ' + t.type)


def analyze(input_file, output_file=None):
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            code = f.read()
    except FileNotFoundError:
        print(f"Ошибка: файл '{input_file}' не найден")
        sys.exit(1)

    tokens, errors = tokenize(code)

    lines = []
    lines.append('Лексема'.ljust(22) + '| Тип')
    lines.append('-' * 22 + '+' + '-' * 20)
    for t in tokens:
        lines.append(t.value.ljust(22) + '| ' + t.type)
    lines.append('')

    # последовательность лексем для синтаксического анализатора
    seq = [(t.type, t.value) for t in tokens]
    lines.append(str(seq))
    lines.append('')

    if errors:
        for e in errors:
            lines.append(e)
        lines.append(f'Лексический анализ завершен с ошибками. '
                     f'Обнаружено ошибок: {len(errors)}.')
    else:
        lines.append(f'Лексический анализ завершен успешно. '
                     f'Обнаружено {len(tokens)} токенов. Ошибок не найдено.')

    result = '\n'.join(lines)

    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(result)
        print(f'Результат сохранен в файл: {output_file}')
    else:
        print(result)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Использование: python lexer.py <входной_файл> [выходной_файл]')
        print('Пример: python3 lexer.py cleaned.cpp result.txt')
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    analyze(input_file, output_file)
