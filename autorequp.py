import os
import sys
import argparse

from itertools import takewhile, dropwhile


def parse_requirements_file(requirements_file):
    requirements = {}
    with open(requirements_file, "r") as f:
        for line in f.read().split("\n"):
            # ignore comments
            if line.strip().startswith("#"):
                continue

            line = line.strip()

            name = "".join(takewhile(lambda x: x not in ("<", ">", "=", "!"), line))
            conditions = "".join(dropwhile(lambda x: x not in ("<", ">", "=", "!"), line)).split(",")

            requirements[name] = conditions

    return requirements


def main():
    parser = argparse.ArgumentParser(description='Auto-upgrade python dependencies of a project.')
    parser.add_argument('-r', '--requirements', help='frozen requirements.txt file', required=True)
    parser.add_argument('-t', '--test-command', help='test command to launch to validate that everything is ok', required=True)

    args = parser.parse_args()

    if not os.path.exists(args.requirements):
        print(f"Error: requirements file '{args.requirements}' doesn't exist")
        sys.exit(1)

    requirements = parse_requirements_file(args.requirements)

    print(requirements)


if __name__ == '__main__':
    main()
