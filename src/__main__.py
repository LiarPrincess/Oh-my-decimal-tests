import os
import sys
import test_next
import test_round
import test_unary
import test_quantum
import test_compare
import test_remainder
import test_properties
import test_logb_scaleb_py
import test_other


def main():
    output_dir = "output"

    if len(sys.argv) == 2:
        output_dir = sys.argv[1]

    _clean_dir(output_dir)
    test_next.write(output_dir)
    test_round.write(output_dir)
    test_unary.write(output_dir)
    test_quantum.write(output_dir)
    test_compare.write(output_dir)
    test_remainder.write(output_dir)
    test_properties.write(output_dir)
    test_logb_scaleb_py.write(output_dir)
    test_other.write(output_dir)


def _clean_dir(dir: str):
    os.makedirs(dir, exist_ok=True)

    for name in os.listdir(dir):
        path = os.path.join(dir, name)
        os.unlink(path)

    gitkeep_path = os.path.join(dir, ".gitkeep")
    with open(gitkeep_path, "w") as f:
        pass


if __name__ == "__main__":
    main()
