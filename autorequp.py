#!/usr/bin/env python3

import os
import re
import sys
import operator
import argparse
import subprocess

from itertools import takewhile, dropwhile
from distlib.version import LegacyVersion

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
            conditions = "".join(dropwhile(lambda x: x not in ("<", ">", "=", "!"), line))

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


def filter_pkg_that_can_be_upgraded(depends):
    no_upgrades = []
    new_depends = {}

    for key, value in depends.items():
        conditions = parse_conditions(value["current_version_scheme"])

        if conditions is None:
            print("No specified version for %s, drop it" % key)
            continue

        compatible_versions = value["all_versions"]

        for (op, version) in conditions:
            compatible_versions = [x for x in compatible_versions if op(LegacyVersion(x["version"]), LegacyVersion(version))]

        maximum_version = list(sorted(compatible_versions, key=lambda x: LegacyVersion(x["version"])))[-1]
        all_versions_sorted = sorted(value["all_versions"], key=lambda x: LegacyVersion(x["version"]))
        possible_upgrades = list(dropwhile(lambda x: LegacyVersion(x["version"]) <= LegacyVersion(maximum_version["version"]), all_versions_sorted))

        if possible_upgrades:
            new_depends[key] = value
            new_depends[key]["possible_upgrades"] = possible_upgrades
        else:
            no_upgrades.append(key)

    if no_upgrades:
        print("Skipped packages that don't need to be upgraded: %s" % (", ".join(no_upgrades)))

    if new_depends:
        print("")
        print("Packages that can upgrades with all those available verisons:")
        for key, value in new_depends.items():
            print("* %s (%s) to %s" % (key, value["current_version_scheme"], ", ".join(map(lambda x: x["version"], value["possible_upgrades"]))))

    return new_depends


def parse_conditions(conditions):
    string_to_operator = {
        "==": operator.eq,
        "<": operator.lt,
        "<=": operator.le,
        "!=": operator.ne,
        ">=": operator.ge,
        ">": operator.gt,
    }

    parsed_conditions = []

    if not conditions:
        return None

    for i in conditions.split(","):
        version_operator, version_number = re.match("(==|>=|<=|>|<) *([0-9.]*)", i.strip()).groups()

        parsed_conditions.append([
            string_to_operator[version_operator],
            version_number,
        ])

    return parsed_conditions


def try_to_upgrade_dependencies(test_command, requirements, requirements_file):
    # TODO explore different strategies like:
    # - max_upgrade first
    # - be aware of semantic versionning to jump between non-breaking versions
    # - bisect

    # TODO handle the situation when a requirement need other requirements to
    # be upgraded too

    for name, requirement in requirements.items():
        for possible_upgrade in requirement["possible_upgrades"]:
            version = possible_upgrade["version"]
            previous_version = change_version(name, version, requirements_file)

            try:
                subprocess.check_call(test_command, shell=True)
            except subprocess.CalledProcessError:
                print(f"[FAILED] {name} → {version}, rollback to {previous_version}")
                # rollback_version(previous_version, requirements_file)
                break
            else:
                print(f"[SUCCESS] {name} → {version}")


def change_version(pkg_name, version, requirements_file):
    lines = []
    with open(requirements_file, "r") as f:
        for line in f.read().split("\n"):
            # XXX here we don't take the "[stuff]"
            name = "".join(takewhile(lambda x: x not in ("<", ">", "=", "!", "["), line))
            previous_version = "".join(dropwhile(lambda x: x not in ("<", ">", "=", "!"), line))
            if name == pkg_name:
                # dep[special_config]
                if "[" in line:
                    name = line.split("[")

                line = f"{name}=={version}"

            lines.append(line)

    with open(requirements_file, "w") as f:
        f.write("\n".join(lines))

    return previous_version


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

    requirements = filter_pkg_that_can_be_upgraded(requirements)

    if not requirements:
        print("")
        print("Nothing to do, everything is up to date")
        sys.exit(0)

    try_to_upgrade_dependencies(args.test_command, requirements, requirements_file=args.requirements)


if __name__ == '__main__':
    main()
