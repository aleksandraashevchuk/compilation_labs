import sys

# Объединение всех модулей компилятора (ЛР1 - ЛР4)
from preprocessor import (                        # ЛР1: препроцессор
    validate_comments, remove_comments, clean_whitespace, check_invalid_chars,
)
from lexer import tokenize                        # ЛР2: лексический анализатор
from parser import Parser, ParseError             # ЛР3: синтаксический анализатор
from semantic import SemanticAnalyzer, print_symbol_table, print_triads  # ЛР4


def compile_program(input_file):
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            source = f.read()
    except FileNotFoundError:
        print(f"Ошибка: файл '{input_file}' не найден")
        sys.exit(1)

    print('ЭТАП 1. ПРЕПРОЦЕССИНГ (ЛР1)')
    try:
        validate_comments(source)
        cleaned = remove_comments(source)
        check_invalid_chars(cleaned)
        cleaned = clean_whitespace(cleaned)
    except (SyntaxError, ValueError) as e:
        print(f'Ошибка препроцессора: {e}')
        sys.exit(1)
    print('Комментарии, лишние пробелы и пустые строки удалены.')
    print('Очищенный код получен.')
    print()

    print('ЭТАП 2. ЛЕКСИЧЕСКИЙ АНАЛИЗ (ЛР2)')
    tokens, lex_errors = tokenize(cleaned)
    if lex_errors:
        for e in lex_errors:
            print(' ', e)
        sys.exit(1)
    print(f'Получено токенов: {len(tokens)}.')
    print()

    print('ЭТАП 3. СИНТАКСИЧЕСКИЙ АНАЛИЗ (ЛР3)')
    try:
        program = Parser(tokens).parse_program()
    except ParseError as e:
        print(f"Синтаксическая ошибка: {e}")
        sys.exit(1)
    print('Абстрактное синтаксическое дерево построено.')
    print()

    print('ЭТАП 4. СЕМАНТИЧЕСКИЙ АНАЛИЗ И ГЕНЕРАЦИЯ ТРИАД (ЛР4)')
    analyzer = SemanticAnalyzer()
    analyzer.analyze(program)
    print_symbol_table(analyzer.symbols)
    print()
    if analyzer.errors:
        print('Обнаружены семантические ошибки:')
        for e in analyzer.errors:
            print(' ', e)
        sys.exit(1)
    print('Семантический анализ завершен успешно. Ошибок не найдено.')
    print()
    print_triads(analyzer.triads)
    print()
    print('Компиляция завершена успешно.')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Использование: python compiler.py <исходный_файл>')
        print('Пример: python3 compiler.py test.cpp')
        sys.exit(1)
    compile_program(sys.argv[1])
