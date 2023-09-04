from execo_engine import ParamSweeper
import os
import sys

args = sys.argv
if len(args) > 1:
    detail = True
else:
    detail = False


for i in range(100):
    sweeper_path = f"esds-executions-runs/{i}/sweeper"
    if os.path.exists(sweeper_path) and os.path.getsize(f"{sweeper_path}/sweeps") > 0:
        print(f"Sweeper {i}: ", end="")
        sweeper = ParamSweeper(sweeper_path)
        print(sweeper)
        if detail:
            print("In progress:")
            for ip in sweeper.get_inprogress():
                print(f"  - {ip}")
            print("Remaining:")
            for r in sweeper.get_remaining():
                print(f"  - {r}")

    else:
        print(f"Sweeper {i}: no experiment done")
