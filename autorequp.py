import os
import sys
import argparse


def main():
    parser = argparse.ArgumentParser(description='Auto-upgrade python dependencies of a project.')
    parser.add_argument('-r', '--requirements', help='frozen requirements.txt file', required=True)
    parser.add_argument('-t', '--test-command', help='test command to launch to validate that everything is ok', required=True)

    args = parser.parse_args()

    if not os.path.exists(args.requirements):
        print(f"Error: requirements file '{args.requirements}' doesn't exist")
        sys.exit(1)


if __name__ == '__main__':
    main()
