#include <iostream>
#include <string>

// функция вычисления степени числа
int step(int base, int exp) {
    int result = 1;
    for (int i = 0; i < exp; ++i) { /* цикл умножения */
        result *= base;
    }
    return result;
}

int main() {
    // объявление переменных и присваивание
    int x = 3;
    int n = 4;

    // арифметическое выражение
    int val = step(x, n) - x * 2;

    // логическое выражение
    bool is_positive = (val > 0) && (x != 0);

    // условный оператор if-else
    if (is_positive) {
        std::cout << "val = " << val << " (positive)\n";
    } else {
        std::cout << "val = " << val << " (non-positive)\n";
    }

    /* вывод таблицы степеней */
    for (int i = 1; i <= 5; ++i) {
        std::cout << x << "^" << i << " = " << step(x, i) << "\n";
    }

    return 0;
}
