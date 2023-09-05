import time


def fibo(n):
    s = time.time()
    a,b=0,0
    while n>0:
        a,b=b,a+b
        n-=1
    print(f"done in {round(time.time() - s, 2)}s")

import multiprocessing
import threading

print("Multithreading times")
l = []
for i in range(4):
    t = threading.Thread(target=fibo, args=(100000000,))
    t.start()
    l.append(t)

i = 0
for p in l:
    p.join()
    i += 1

print()
print("Multiprocessing times")
l = []
for i in range(4):
    t = multiprocessing.Process(target=fibo, args=(100000000,))
    t.start()
    l.append(t)

i = 0
for p in l:
    p.join()
    i += 1
