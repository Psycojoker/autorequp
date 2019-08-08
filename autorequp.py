#!/usr/bin/env python3

import os
import sys
import argparse

from itertools import takewhile, dropwhile

import requests


def parse_requirements_file(requirements_file):
    requirements = {}
    with open(requirements_file, "r") as f:
        for line in f.read().split("\n"):
            # ignore comments and blank lines
            if not line.strip() or line.strip().startswith("#"):
                continue

            line = line.strip()

            name = "".join(takewhile(lambda x: x not in ("<", ">", "=", "!"), line))
            conditions = "".join(dropwhile(lambda x: x not in ("<", ">", "=", "!"), line)).split(",")

            requirements[name] = conditions

    return requirements


def merge_depends_with_pypi_info(depends):
    new_depends = {}

    for key, value in depends.items():
        pkg_name = key.split("[", 1)[0]

        print("Get all releases of %s..." % pkg_name)
        response = requests.get("https://pypi.org/pypi/%s/json" % pkg_name, timeout=30)
        if response.status_code == 404:
            print("Warning: %s doesn't exist on pypi, skip it" % pkg_name)
            continue

        data = response.json()

        all_versions = []

        for key2, value2 in data["releases"].items():
            # sometime we don't have metadata information for a release :|
            all_versions.append(value2[0] if value2 else {})
            all_versions[-1]["version"] = key2

        new_depends[key] = {
            "pkg_name": pkg_name,
            "current_version_scheme": value,
            "all_versions": all_versions
        }

    return new_depends


def main():
    parser = argparse.ArgumentParser(description='Auto-upgrade python dependencies of a project.')
    parser.add_argument('-r', '--requirements', help='frozen requirements.txt file', required=True)
    parser.add_argument('-t', '--test-command', help='test command to launch to validate that everything is ok', required=True)

    args = parser.parse_args()

    if not os.path.exists(args.requirements):
        print(f"Error: requirements file '{args.requirements}' doesn't exist")
        sys.exit(1)

    requirements = parse_requirements_file(args.requirements)

    requirements = merge_depends_with_pypi_info(requirements)

    print(requirements)


if __name__ == '__main__':
    main()
