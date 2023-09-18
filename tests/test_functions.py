def print_assertions(title: str, expected_val: float, val: float):
    rounded_val = round(val, 2)
    if not expected_val == rounded_val:
        print(f"AssertionError: {title} {expected_val} != {rounded_val}")
