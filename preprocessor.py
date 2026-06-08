import re
import sys


# Регулярные выражения
BLOCK_COMMENT = re.compile(r'/\*.*?\*/', re.DOTALL)    # /* ... */
LINE_COMMENT  = re.compile(r'//.*?$',    re.MULTILINE) # // ...
INVALID_CHARS = re.compile(r'[^\x20-\x7E\n\r\t]')      # не-ASCII символы


def validate_comments(code):
    # проверяет, что все блочные комментарии закрыты
    opens  = len(re.findall(r'/\*', code))
    closes = len(re.findall(r'\*/', code))
    if opens != closes:
        raise SyntaxError("Обнаружен незакрытый многострочный комментарий '/*'")


def remove_comments(code):
    # удаляет однострочные и многострочные комментарии
    code = BLOCK_COMMENT.sub('', code)
    code = LINE_COMMENT.sub('', code)
    return code


def clean_whitespace(code):
    # удаляет лишние пробелы и пустые строки
    lines = code.split('\n')
    result = []
    for line in lines:
        stripped = line.strip()
        if stripped:
            result.append(stripped)
    return '\n'.join(result)


def check_invalid_chars(code):
    # проверяет наличие недопустимых символов
    found = INVALID_CHARS.findall(code)
    if found:
        unique = set(found)
        raise ValueError(f"Обнаружены недопустимые символы: {unique}")


def preprocess(input_file, output_file=None):
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            code = f.read()

        validate_comments(code)
        code = remove_comments(code)
        check_invalid_chars(code)
        code = clean_whitespace(code)

        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(code)
            print(f"Результат сохранен в файл: {output_file}")
        else:
            print(code)

        print("Ошибок не выявлено")

    except FileNotFoundError:
        print(f"Ошибка: файл '{input_file}' не найден")
        sys.exit(1)
    except SyntaxError as e:
        print(f"Синтаксическая ошибка: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"Ошибка: {e}")
        sys.exit(1)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Использование: python preprocessor.py <входной_файл> [выходной_файл]")
        print("Пример: python preprocessor.py test.cpp cleaned.cpp")
        sys.exit(1)

    input_file  = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    preprocess(input_file, output_file)
