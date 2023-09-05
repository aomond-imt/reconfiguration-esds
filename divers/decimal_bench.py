import time
from decimal import Decimal

s = 0
start = time.time()
n = 50_000_000
for i in range(n):
    s += (Decimal(i/2) + Decimal('2.71') * Decimal('3.95')) / Decimal('4.32') - Decimal(str(i/3))
print(f"Decimal: {s} - {round(time.time() - start, 2)}s")

s = 0
start = time.time()
for i in range(n):
    s += (i/2 + 2.71 * 3.95) / 4.32 - i/3
print(f"Float: {s} - {round(time.time() - start, 2)}s")
