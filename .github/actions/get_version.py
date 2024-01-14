import json  # noqa: D100
import sys


def main():  # noqa: D103
    with open("./custom_components/ecotrend_ista/manifest.json") as json_file:
        data = json.load(json_file)
        print(data["version"])  # noqa: T201
    return 0


if __name__ == "__main__":
    sys.exit(main())
