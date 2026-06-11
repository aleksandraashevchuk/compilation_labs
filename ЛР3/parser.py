import sys
from dataclasses import dataclass, field
from typing import List, Optional

# Лексический анализатор из ЛР2 используется для получения потока токенов
from lexer import tokenize, Token



#AST
@dataclass
class Program:
    includes: List['Include'] = field(default_factory=list)
    functions: List['FuncDecl'] = field(default_factory=list)


@dataclass
class Include:
    name: str


@dataclass
class FuncDecl:
    return_type: str
    name: str
    params: List['Param']
    body: 'Block'


@dataclass
class Param:
    var_type: str
    name: str


@dataclass
class Block:
    statements: list


@dataclass
class VarDecl:
    var_type: str
    name: str
    init: object


@dataclass
class AssignStmt:
    op: str
    target: object
    value: object


@dataclass
class ForStmt:
    init: object
    condition: object
    update: object
    body: 'Block'


@dataclass
class IfStmt:
    condition: object
    then_block: 'Block'
    else_block: Optional['Block']


@dataclass
class ReturnStmt:
    value: object


@dataclass
class ExprStmt:
    expr: object


@dataclass
class BinaryOp:
    op: str
    left: object
    right: object


@dataclass
class UnaryOp:
    op: str
    operand: object


@dataclass
class Call:
    callee: object
    args: list


@dataclass
class Identifier:
    name: str


@dataclass
class IntLiteral:
    value: str


@dataclass
class StringLiteral:
    value: str


@dataclass
class BoolLiteral:
    value: str


# ИСКЛЮЧЕНИЕ СИНТАКСИЧЕСКОЙ ОШИБКИ
class ParseError(Exception):
    pass


# Типы-ключевые слова, обозначающие тип данных
TYPE_KEYWORDS = {'int', 'bool', 'float', 'double', 'char', 'void'}

# Таблица приоритетов бинарных операторов (чем больше, тем выше приоритет)
PRECEDENCE = {
    '||': 1, '&&': 2,
    '==': 3, '!=': 3,
    '<': 4, '>': 4, '<=': 4, '>=': 4,
    '<<': 5, '>>': 5,
    '+': 6, '-': 6,
    '*': 7, '/': 7, '%': 7,
}

ASSIGN_OPS = {'=', '+=', '-=', '*=', '/='}


# СИНТАКСИЧЕСКИЙ АНАЛИЗАТОР (метод рекурсивного спуска)
class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.pos = 0

    # вспомогательные методы
    def current(self) -> Optional[Token]:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def at_end(self) -> bool:
        return self.pos >= len(self.tokens)

    def check(self, type_=None, value=None) -> bool:
        t = self.current()
        if t is None:
            return False
        if type_ is not None and t.type != type_:
            return False
        if value is not None and t.value != value:
            return False
        return True

    def advance(self) -> Token:
        t = self.tokens[self.pos]
        self.pos += 1
        return t

    def expect(self, type_=None, value=None) -> Token:
        t = self.current()
        if t is None:
            raise ParseError(
                f"неожиданный конец потока токенов (позиция {self.pos}): "
                f"ожидался {value or type_}")
        if (type_ is not None and t.type != type_) or (value is not None and t.value != value):
            exp = value if value is not None else type_
            raise ParseError(
                f"неожиданный токен ({t.type}, '{t.value}') в позиции {self.pos}: "
                f"ожидался '{exp}'")
        return self.advance()

    # грамматика
    def parse_program(self) -> Program:
        prog = Program()
        while not self.at_end():
            if self.check('KEYWORD', '#include'):
                prog.includes.append(self.parse_include())
            elif self.check('KEYWORD') and self.current().value in TYPE_KEYWORDS:
                prog.functions.append(self.parse_func_decl())
            else:
                t = self.current()
                raise ParseError(
                    f"неожиданный токен ({t.type}, '{t.value}') в позиции {self.pos}: "
                    f"ожидалась директива #include или объявление функции")
        return prog

    def parse_include(self) -> Include:
        self.expect('KEYWORD', '#include')
        self.expect('OPERATOR', '<')
        name = self.expect('IDENTIFIER').value
        self.expect('OPERATOR', '>')
        return Include(name)

    def parse_func_decl(self) -> FuncDecl:
        return_type = self.advance().value           # тип возврата
        name = self.expect('IDENTIFIER').value       # имя функции
        self.expect('DELIMITER', '(')
        params = self.parse_params()
        self.expect('DELIMITER', ')')
        body = self.parse_block()
        return FuncDecl(return_type, name, params, body)

    def parse_params(self) -> List[Param]:
        params = []
        if self.check('DELIMITER', ')'):
            return params
        while True:
            ptype = self.advance().value
            pname = self.expect('IDENTIFIER').value
            params.append(Param(ptype, pname))
            if self.check('DELIMITER', ','):
                self.advance()
                continue
            break
        return params

    def parse_block(self) -> Block:
        self.expect('DELIMITER', '{')
        stmts = []
        while not self.check('DELIMITER', '}'):
            if self.at_end():
                raise ParseError(
                    f"непарная скобка: незакрытый блок '{{' "
                    f"(достигнут конец потока, ожидался '}}')")
            stmts.append(self.parse_statement())
        self.expect('DELIMITER', '}')
        return Block(stmts)

    def parse_statement(self):
        t = self.current()
        if t.type == 'KEYWORD' and t.value in TYPE_KEYWORDS:
            return self.parse_var_decl()
        if self.check('KEYWORD', 'for'):
            return self.parse_for()
        if self.check('KEYWORD', 'if'):
            return self.parse_if()
        if self.check('KEYWORD', 'return'):
            return self.parse_return()
        if self.check('DELIMITER', '{'):
            return self.parse_block()
        return self.parse_expr_statement()

    def parse_var_decl(self) -> VarDecl:
        var_type = self.advance().value
        name = self.expect('IDENTIFIER').value
        self.expect('OPERATOR', '=')
        init = self.parse_expression()
        self.expect('DELIMITER', ';')
        return VarDecl(var_type, name, init)

    def parse_for(self) -> ForStmt:
        self.expect('KEYWORD', 'for')
        self.expect('DELIMITER', '(')
        # инициализация
        if self.check('KEYWORD') and self.current().value in TYPE_KEYWORDS:
            init = self.parse_var_decl()             # сам поглощает ';'
        else:
            init = self.parse_expression()
            self.expect('DELIMITER', ';')
        # условие
        condition = self.parse_expression()
        self.expect('DELIMITER', ';')
        # обновление
        update = self.parse_expression()
        self.expect('DELIMITER', ')')
        body = self.parse_block()
        return ForStmt(init, condition, update, body)

    def parse_if(self) -> IfStmt:
        self.expect('KEYWORD', 'if')
        self.expect('DELIMITER', '(')
        condition = self.parse_expression()
        self.expect('DELIMITER', ')')
        then_block = self.parse_block()
        else_block = None
        if self.check('KEYWORD', 'else'):
            self.advance()
            if self.check('KEYWORD', 'if'):
                else_block = self.parse_if()
            else:
                else_block = self.parse_block()
        return IfStmt(condition, then_block, else_block)

    def parse_return(self) -> ReturnStmt:
        self.expect('KEYWORD', 'return')
        value = None
        if not self.check('DELIMITER', ';'):
            value = self.parse_expression()
        self.expect('DELIMITER', ';')
        return ReturnStmt(value)

    def parse_expr_statement(self):
        expr = self.parse_expression()
        # присваивание?
        if self.check('OPERATOR') and self.current().value in ASSIGN_OPS:
            op = self.advance().value
            value = self.parse_expression()
            self.expect('DELIMITER', ';')
            return AssignStmt(op, expr, value)
        self.expect('DELIMITER', ';')
        return ExprStmt(expr)

    # выражения (метод приоритетов операторов)
    def parse_expression(self, min_prec=0):
        left = self.parse_unary()
        while (self.check('OPERATOR') and self.current().value in PRECEDENCE
               and PRECEDENCE[self.current().value] >= min_prec):
            op = self.advance().value
            right = self.parse_expression(PRECEDENCE[op] + 1)
            left = BinaryOp(op, left, right)
        return left

    def parse_unary(self):
        if self.check('OPERATOR') and self.current().value in ('++', '--', '-', '!'):
            op = self.advance().value
            operand = self.parse_unary()
            return UnaryOp(op, operand)
        return self.parse_postfix()

    def parse_postfix(self):
        node = self.parse_primary()
        while self.check('DELIMITER', '('):
            self.advance()
            args = []
            if not self.check('DELIMITER', ')'):
                args.append(self.parse_expression())
                while self.check('DELIMITER', ','):
                    self.advance()
                    args.append(self.parse_expression())
            self.expect('DELIMITER', ')')
            node = Call(node, args)
        return node

    def parse_primary(self):
        t = self.current()
        if t is None:
            raise ParseError("неожиданный конец потока токенов в выражении")
        if t.type == 'CONSTANT_INT':
            self.advance()
            return IntLiteral(t.value)
        if t.type == 'CONSTANT_STRING':
            self.advance()
            return StringLiteral(t.value)
        if t.type == 'CONSTANT_BOOL':
            self.advance()
            return BoolLiteral(t.value)
        if t.type == 'IDENTIFIER':
            self.advance()
            name = t.value
            # квалифицированное имя std::cout
            while self.check('OPERATOR', '::'):
                self.advance()
                part = self.expect('IDENTIFIER').value
                name += '::' + part
            return Identifier(name)
        if self.check('DELIMITER', '('):
            self.advance()
            expr = self.parse_expression()
            self.expect('DELIMITER', ')')
            return expr
        raise ParseError(
            f"неожиданный токен ({t.type}, '{t.value}') в позиции {self.pos}: "
            f"ожидалось выражение")


# ВЫВОД AST В ВИДЕ ДЕРЕВА
def build_tree(node):
    # преобразует узел AST в пару (подпись, список потомков) для печати
    if isinstance(node, Program):
        children = [build_tree(inc) for inc in node.includes]
        children += [build_tree(fn) for fn in node.functions]
        return ("Program", children)
    if isinstance(node, Include):
        return (f"include: {node.name}", [])
    if isinstance(node, FuncDecl):
        ch = [(f"return_type: {node.return_type}", [])]
        if node.params:
            ch.append(("params", [(f"param: {p.name} ({p.var_type})", []) for p in node.params]))
        ch.append(("body", [build_tree(s) for s in node.body.statements]))
        return (f"func_decl: {node.name}", ch)
    if isinstance(node, Block):
        return ("block", [build_tree(s) for s in node.statements])
    if isinstance(node, VarDecl):
        return (f"var_decl: {node.name}", [
            (f"type: {node.var_type}", []),
            ("init", [build_tree(node.init)]),
        ])
    if isinstance(node, AssignStmt):
        return (f"assign_stmt: {node.op}", [
            ("left", [build_tree(node.target)]),
            ("right", [build_tree(node.value)]),
        ])
    if isinstance(node, ForStmt):
        return ("for_stmt", [
            ("init", [build_tree(node.init)]),
            ("condition", [build_tree(node.condition)]),
            ("update", [build_tree(node.update)]),
            ("body", [build_tree(s) for s in node.body.statements]),
        ])
    if isinstance(node, IfStmt):
        ch = [
            ("condition", [build_tree(node.condition)]),
            ("then", [build_tree(s) for s in node.then_block.statements]),
        ]
        if node.else_block is not None:
            if isinstance(node.else_block, Block):
                ch.append(("else", [build_tree(s) for s in node.else_block.statements]))
            else:
                ch.append(("else", [build_tree(node.else_block)]))
        return ("if_stmt", ch)
    if isinstance(node, ReturnStmt):
        ch = [] if node.value is None else [("value", [build_tree(node.value)])]
        return ("return_stmt", ch)
    if isinstance(node, ExprStmt):
        return ("expr_stmt", [build_tree(node.expr)])
    if isinstance(node, BinaryOp):
        return (f"op '{node.op}'", [
            ("left", [build_tree(node.left)]),
            ("right", [build_tree(node.right)]),
        ])
    if isinstance(node, UnaryOp):
        return (f"unary '{node.op}'", [build_tree(node.operand)])
    if isinstance(node, Call):
        ch = [("function", [build_tree(node.callee)])]
        if node.args:
            ch.append(("args", [build_tree(a) for a in node.args]))
        return ("call", ch)
    if isinstance(node, Identifier):
        return (f"id: {node.name}", [])
    if isinstance(node, IntLiteral):
        return (f"int: {node.value}", [])
    if isinstance(node, StringLiteral):
        return (f"string: {node.value}", [])
    if isinstance(node, BoolLiteral):
        return (f"bool: {node.value}", [])
    return (str(node), [])


def render_tree(tree, prefix="", is_last=True, is_root=True, out=None):
    label, children = tree
    if is_root:
        out.append(label)
    else:
        out.append(prefix + ("└── " if is_last else "├── ") + label)
        prefix += "    " if is_last else "│   "
    for i, child in enumerate(children):
        render_tree(child, prefix, i == len(children) - 1, False, out)


# ТОЧКА ВХОДА
def analyze(input_file):
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            code = f.read()
    except FileNotFoundError:
        print(f"Ошибка: файл '{input_file}' не найден")
        sys.exit(1)

    # этап 1: лексический анализ (ЛР2)
    tokens, lex_errors = tokenize(code)
    if lex_errors:
        print("Обнаружены лексические ошибки:")
        for e in lex_errors:
            print(" ", e)
        sys.exit(1)

    # этап 2: синтаксический анализ (рекурсивный спуск)
    parser = Parser(tokens)
    try:
        program = parser.parse_program()
    except ParseError as e:
        print(f"Синтаксическая ошибка: {e}")
        sys.exit(1)

    lines = []
    render_tree(build_tree(program), out=lines)
    print('\n'.join(lines))
    print()
    print("Синтаксический анализ завершен успешно. Ошибок не найдено.")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Использование: python parser.py <входной_файл>")
        print("Пример: python3 parser.py cleaned.cpp")
        sys.exit(1)
    analyze(sys.argv[1])
