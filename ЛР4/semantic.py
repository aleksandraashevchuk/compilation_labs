import sys
from dataclasses import dataclass

# Модули предыдущих лабораторных работ
from lexer import tokenize
from parser import (
    Parser, ParseError,
    Program, Include, FuncDecl, Param, Block, VarDecl, AssignStmt,
    ForStmt, IfStmt, ReturnStmt, ExprStmt, BinaryOp, UnaryOp, Call,
    Identifier, IntLiteral, StringLiteral, BoolLiteral,
)


# ТАБЛИЦА СИМВОЛОВ
@dataclass
class Symbol:
    name: str
    type: str
    scope: str
    declared: bool
    initialized: bool


# Внешние идентификаторы, объявленные в подключаемых заголовках
EXTERNAL = {'std', 'cout', 'endl', 'iostream', 'string'}

# Типы результата операций
ARITH_OPS = {'+', '-', '*', '/', '%'}
COMPARE_OPS = {'<', '>', '<=', '>=', '==', '!='}
LOGIC_OPS = {'&&', '||'}


class SemanticError(Exception):
    pass


class SemanticAnalyzer:
    def __init__(self):
        self.scopes = [{}]          # стек областей видимости (имя -> Symbol)
        self.scope_names = ['global']  # стек имен областей
        self.functions = {}         # имя функции -> тип возврата
        self.symbols = []           # все символы для таблицы
        self.errors = []            # семантические ошибки
        self.triads = []            # промежуточное представление

    @property
    def scope_name(self):
        return self.scope_names[-1]

    # область видимости
    def push_scope(self, name):
        self.scopes.append({})
        self.scope_names.append(name)

    def pop_scope(self):
        self.scopes.pop()
        self.scope_names.pop()

    def declare(self, name, type_, initialized):
        current = self.scopes[-1]
        if name in current:
            self.errors.append(
                f"повторное объявление переменной '{name}' в области '{self.scope_name}'")
            return
        sym = Symbol(name, type_, self.scope_name, True, initialized)
        current[name] = sym
        self.symbols.append(sym)

    def lookup(self, name):
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    # триады
    def emit(self, op, a, b='-'):
        self.triads.append([op, a, b])
        return len(self.triads)          # номер триады (с единицы)

    # ОБХОД AST
    def analyze(self, program: Program):
        # предварительная регистрация функций
        for fn in program.functions:
            self.functions[fn.name] = fn.return_type
            self.symbols.append(Symbol(fn.name, f'function -> {fn.return_type}',
                                       'global', True, True))
        for fn in program.functions:
            self.visit_func(fn)

    def visit_func(self, fn: FuncDecl):
        self.emit('PROC', fn.name)
        self.push_scope(fn.name)
        for p in fn.params:
            self.declare(p.name, p.var_type, True)
        for stmt in fn.body.statements:
            self.visit_stmt(stmt)
        self.pop_scope()

    def visit_stmt(self, node):
        if isinstance(node, VarDecl):
            self.visit_var_decl(node)
        elif isinstance(node, AssignStmt):
            self.visit_assign(node)
        elif isinstance(node, ForStmt):
            self.visit_for(node)
        elif isinstance(node, IfStmt):
            self.visit_if(node)
        elif isinstance(node, ReturnStmt):
            self.visit_return(node)
        elif isinstance(node, ExprStmt):
            self.visit_expr_stmt(node)
        elif isinstance(node, Block):
            for s in node.statements:
                self.visit_stmt(s)

    def visit_var_decl(self, node: VarDecl):
        operand, expr_type = self.gen_expr(node.init)
        # проверка совместимости типов
        if expr_type is not None and expr_type != node.var_type and expr_type != 'unknown':
            self.errors.append(
                f"несоответствие типов: переменной '{node.name}' типа "
                f"'{node.var_type}' присваивается значение типа '{expr_type}'")
        self.declare(node.name, node.var_type, True)
        self.emit(':=', node.name, operand)

    def visit_assign(self, node: AssignStmt):
        target = node.target
        if isinstance(target, Identifier):
            sym = self.lookup(target.name)
            if sym is None and target.name not in EXTERNAL:
                self.errors.append(
                    f"использование необъявленной переменной '{target.name}'")
            tname = target.name
            ttype = sym.type if sym else 'unknown'
        else:
            tname, ttype = self.gen_expr(target)

        operand, vtype = self.gen_expr(node.value)
        if node.op == '=':
            if ttype not in ('unknown', None) and vtype not in ('unknown', None) and ttype != vtype:
                self.errors.append(
                    f"несоответствие типов в присваивании переменной '{tname}': "
                    f"'{ttype}' и '{vtype}'")
            self.emit(':=', tname, operand)
        else:
            # составное присваивание: a *= b  =>  (*, a, b); (:=, a, ^k)
            base_op = node.op[0]
            ref = self.emit(base_op, tname, operand)
            self.emit(':=', tname, f'^{ref}')

    def visit_for(self, node: ForStmt):
        self.push_scope(self.scope_name + '.for')
        self.visit_stmt(node.init)
        cond_label = len(self.triads) + 1
        cond_operand, _ = self.gen_expr(node.condition)
        jf_index = self.emit('JF', cond_operand, '?')
        for s in node.body.statements:
            self.visit_stmt(s)
        # обновление (например, ++i)
        self.gen_expr_or_update(node.update)
        self.emit('JMP', f'({cond_label})')
        end_label = len(self.triads) + 1
        self.triads[jf_index - 1][2] = f'({end_label})'
        self.pop_scope()

    def visit_if(self, node: IfStmt):
        cond_operand, _ = self.gen_expr(node.condition)
        jf_index = self.emit('JF', cond_operand, '?')
        self.push_scope(self.scope_name + '.if')
        for s in node.then_block.statements:
            self.visit_stmt(s)
        self.pop_scope()
        if node.else_block is not None:
            jmp_index = self.emit('JMP', '?')
            else_label = len(self.triads) + 1
            self.triads[jf_index - 1][2] = f'({else_label})'
            self.push_scope(self.scope_name + '.else')
            stmts = node.else_block.statements if isinstance(node.else_block, Block) else [node.else_block]
            for s in stmts:
                self.visit_stmt(s)
            self.pop_scope()
            end_label = len(self.triads) + 1
            self.triads[jmp_index - 1][1] = f'({end_label})'
        else:
            end_label = len(self.triads) + 1
            self.triads[jf_index - 1][2] = f'({end_label})'

    def visit_return(self, node: ReturnStmt):
        if node.value is None:
            self.emit('RET', '-')
        else:
            operand, _ = self.gen_expr(node.value)
            self.emit('RET', operand)

    def visit_expr_stmt(self, node: ExprStmt):
        expr = node.expr
        # поток вывода std::cout << a << b << ...
        if self.is_cout(expr):
            operands = self.flatten_output(expr)
            for op_node in operands:
                operand, _ = self.gen_expr(op_node)
                self.emit('OUT', operand)
        else:
            self.gen_expr_or_update(expr)

    def gen_expr_or_update(self, expr):
        # отдельная обработка инкремента ++i как оператора
        if isinstance(expr, UnaryOp) and expr.op in ('++', '--'):
            operand, _ = self.gen_expr(expr.operand)
            base = '+' if expr.op == '++' else '-'
            ref = self.emit(base, operand, '1')
            self.emit(':=', operand, f'^{ref}')
        else:
            self.gen_expr(expr)

    # распознавание потока вывода
    def is_cout(self, expr):
        node = expr
        while isinstance(node, BinaryOp) and node.op == '<<':
            node = node.left
        return isinstance(node, Identifier) and ('cout' in node.name)

    def flatten_output(self, expr):
        operands = []
        node = expr
        while isinstance(node, BinaryOp) and node.op == '<<':
            operands.append(node.right)
            node = node.left
        # node теперь std::cout — его пропускаем
        operands.reverse()
        return operands

    # ГЕНЕРАЦИЯ ТРИАД ДЛЯ ВЫРАЖЕНИЙ
    # возвращает (операнд, тип)
    def gen_expr(self, node):
        if isinstance(node, IntLiteral):
            return node.value, 'int'
        if isinstance(node, StringLiteral):
            return node.value, 'string'
        if isinstance(node, BoolLiteral):
            return node.value, 'bool'
        if isinstance(node, Identifier):
            if node.name in EXTERNAL or '::' in node.name:
                return node.name, 'external'
            sym = self.lookup(node.name)
            if sym is None:
                self.errors.append(
                    f"использование необъявленной переменной '{node.name}'")
                return node.name, 'unknown'
            return node.name, sym.type
        if isinstance(node, UnaryOp):
            operand, t = self.gen_expr(node.operand)
            if node.op == '!':
                return operand, 'bool'
            ref = self.emit(node.op, operand)
            return f'^{ref}', t
        if isinstance(node, BinaryOp):
            la, lt = self.gen_expr(node.left)
            ra, rt = self.gen_expr(node.right)
            ref = self.emit(node.op, la, ra)
            if node.op in COMPARE_OPS or node.op in LOGIC_OPS:
                rtype = 'bool'
            elif node.op in ARITH_OPS:
                rtype = 'int'
            else:
                rtype = lt
            return f'^{ref}', rtype
        if isinstance(node, Call):
            # вычисление аргументов
            arg_ops = []
            for a in node.args:
                ao, _ = self.gen_expr(a)
                arg_ops.append(ao)
            for ao in arg_ops:
                self.emit('PARAM', ao)
            fname = node.callee.name if isinstance(node.callee, Identifier) else '?'
            ref = self.emit('CALL', fname, str(len(arg_ops)))
            rtype = self.functions.get(fname, 'int')
            return f'^{ref}', rtype
        return '?', 'unknown'


# ВЫВОД РЕЗУЛЬТАТОВ
def print_symbol_table(symbols):
    print('Таблица символов')
    print('Имя'.ljust(14) + 'Тип'.ljust(20) + 'Область'.ljust(16)
          + 'Объявлена'.ljust(12) + 'Инициализирована')
    for s in symbols:
        decl = 'да' if s.declared else 'нет'
        init = 'да' if s.initialized else 'нет'
        print(s.name.ljust(14) + s.type.ljust(20) + s.scope.ljust(16)
              + decl.ljust(12) + init)


def print_triads(triads):
    print('Промежуточное представление (триады):')
    for i, (op, a, b) in enumerate(triads, start=1):
        if b == '-':
            print(f'{i}) ({op}, {a})')
        else:
            print(f'{i}) ({op}, {a}, {b})')


def run(input_file):
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            code = f.read()
    except FileNotFoundError:
        print(f"Ошибка: файл '{input_file}' не найден")
        sys.exit(1)

    # ЛР2: лексический анализ
    tokens, lex_errors = tokenize(code)
    if lex_errors:
        print("Лексические ошибки:")
        for e in lex_errors:
            print(" ", e)
        sys.exit(1)

    # ЛР3: синтаксический анализ
    try:
        program = Parser(tokens).parse_program()
    except ParseError as e:
        print(f"Синтаксическая ошибка: {e}")
        sys.exit(1)

    # ЛР4: семантический анализ
    analyzer = SemanticAnalyzer()
    analyzer.analyze(program)

    print_symbol_table(analyzer.symbols)
    print()
    if analyzer.errors:
        print("Обнаружены семантические ошибки:")
        for e in analyzer.errors:
            print(" ", e)
        print()
    else:
        print("Семантический анализ завершен успешно. Ошибок не найдено.")
        print()
    print_triads(analyzer.triads)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Использование: python semantic.py <входной_файл>")
        print("Пример: python3 semantic.py cleaned.cpp")
        sys.exit(1)
    run(sys.argv[1])
