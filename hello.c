#include <stdio.h>

int main() {
    int a, b, sum;

    // Input two numbers
    printf("Enter first number: ");
    scanf("%d", &a);

    printf("Enter second number: ");
    scanf("%d", &b);

    // Calculate sum
    sum = a * b;

    // Print result
    printf("Sum = %d\n", sum);

    return 0;
}
