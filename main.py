import argparse
import json


def start_group(name: str) -> None:
    print(f"::group::{name}")


def end_group() -> None:
    print("::endgroup::")


def group(msg):
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_group(msg)
            result = func(*args, **kwargs)
            end_group()
            return result

        return wrapper

    return decorator


def error(msg: str) -> None:
    print(f"::error::{msg}")


def debug(msg: str) -> None:
    print(f"::debug::{msg}")


def dispatch_workflow(owner: str, repo: str, event_type: str, payload: dict):
    pass


@group("Inputs")
def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("owner", type=str)
    parser.add_argument("repo", type=str)
    parser.add_argument("event_type", type=str)
    parser.add_argument("payload", type=str)
    args = parser.parse_args()
    args.payload = json.loads(args.payload)

    for k, v in vars(args).items():
        print(f"{k}: {v}")

    return args


def main():
    args = get_args()

    # dispatch wf with random id
    # poll api for wf with id (timeout)
    # poll api for wf status (timeout)
    # exit ok/ko, link to wf
    # if pr, comment link
    pass


if __name__ == "__main__":
    main()
