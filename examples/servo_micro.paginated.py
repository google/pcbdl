from servo_micro import *

for i, page_contents in enumerate(generate_svg(max_pin_count=50)):
    with open(f"servo_micro_page{i}.svg", "w") as f:
        f.write(page_contents)
