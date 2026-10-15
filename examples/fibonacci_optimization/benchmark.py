import time
from calc import fibonacci

start = time.perf_counter()
for _ in range(5):
    fibonacci(30)
elapsed = time.perf_counter() - start
print(f"{elapsed:.6f}")
