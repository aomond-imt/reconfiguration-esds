def compute_per_hour_conso(eScnr, nbONs, nbD):
    print(f"eScnr: {eScnr}J, nbONs: {nbONs}, nbD: {nbD} days")

    per_ON = round(eScnr/nbONs)
    print(f"Per ON: {per_ON}J")
    print(f"Per ON per hour: {round(per_ON/(nbD*24))}J/h")

scnrs = [
    (550_000, 31, 10.36),
    (444_000, 26, 9.98),
    (331_000, 21, 9.31),
    (230_000, 16, 8.63),
    (134_000, 11, 7.53),
    (63_000, 6, 5.97),
    (47_000, 5, 5.35),
    (33_000, 4, 4.72),
    (19_000, 3, 3.7),
    (5_000, 2, 1.52),
]

for eScnr, nbONs, nbD in scnrs:
    compute_per_hour_conso(eScnr, nbONs, nbD)
    print()
