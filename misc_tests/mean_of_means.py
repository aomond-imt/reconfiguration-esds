import numpy as np


pop1 = [1, 1, 2, 3, 10, 94]
pop2 = [2, 2, 4, 5, 23, 27]
pop3 = [32, 9, 329, 325, 253, 217]

means = []
stds = []
for p1, p2, p3 in zip(pop1, pop2, pop3):
    means.append(np.mean([p1, p2, p3]))
    stds.append(np.std([p1, p2, p3])**2)

print(np.mean(stds)**.5)

s1 = np.std(pop1)**2
s2 = np.std(pop2)**2
s3 = np.std(pop3)**2

print(np.mean([s1,s2,s3])**.5)

m1 = np.mean(pop1)
m2 = np.mean(pop2)
m3 = np.mean(pop3)

print(np.mean([m1, m2, m3]), np.mean(means))

s = ((np.std(pop1)**2 + np.std(pop2)**2)/2)**.5

print(s)
print(np.std([m1, m2]), np.std(pop1 + pop2))


