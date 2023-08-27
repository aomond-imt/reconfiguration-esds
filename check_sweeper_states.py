from execo_engine import ParamSweeper
import os

for i in range(5):
    sweeper_path = f"concerto-d-results/{i}/sweeper"
    if os.path.exists(sweeper_path) and os.path.getsize(f"{sweeper_path}/sweeps") > 0:
        print(f"Sweeper {i}: ", end="")
        print(ParamSweeper(sweeper_path))
    else:
        print(f"Sweeper {i}: no experiment done")
