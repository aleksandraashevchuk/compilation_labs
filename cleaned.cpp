#include <iostream>
#include <string>
int step(int base, int exp) {
int result = 1;
for (int i = 0; i < exp; ++i) {
result *= base;
}
return result;
}
int main() {
int x = 3;
int n = 4;
int val = step(x, n) - x * 2;
bool is_positive = (val > 0) && (x != 0);
if (is_positive) {
std::cout << "val = " << val << " (positive)\n";
} else {
std::cout << "val = " << val << " (non-positive)\n";
}
for (int i = 1; i <= 5; ++i) {
std::cout << x << "^" << i << " = " << step(x, i) << "\n";
}
return 0;
}