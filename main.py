import argparse
import json
import sys
import uuid

import requests

# Constants
GITHUB_BASE_URL = "https://api.github.com"


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


@group("Inputs")
def get_args() -> dict:
    parser = argparse.ArgumentParser()
    parser.add_argument("token", type=str)
    parser.add_argument("owner", type=str)
    parser.add_argument("repo", type=str)
    parser.add_argument("event_type", type=str)
    parser.add_argument("payload", type=str)
    args = parser.parse_args()
    args.payload = json.loads(args.payload)

    for k, v in vars(args).items():
        print(f"{k}: {v}")

    return vars(args)


@group("Dispatch workflow")
def dispatch_workflow(
    session: requests.Session,
    owner: str,
    repo: str,
    event_type: str,
    payload: dict,
    **kwargs,
):
    url = f"{GITHUB_BASE_URL}/repos/{owner}/{repo}/dispatches"
    id = str(uuid.uuid4())
    data = {
        "event_type": event_type,
        "client_payload": {
            "id": id,
            "inputs": payload,
        },
    }
    print(f"==> POST: {url}\n", data)
    response = session.post(url, data=json.dumps(data))

    if response.status_code == requests.codes.no_content:
        print(f"Workflow triggered: {id}")
        return id
    else:
        print(f"==> {response.status_code}: Error dispatching workflow!")
        print(response.json())
        sys.exit(1)


def main():
    inputs = get_args()

    # Setup Github session auth
    session = requests.Session()
    session.headers = {"Authorization": f"token {inputs.get('token')}"}

    dispatch_workflow(session, **inputs)
    # poll api for wf with id (timeout)
    # poll api for wf status (timeout)
    # exit ok/ko, link to wf
    # if pr, comment link
    pass


if __name__ == "__main__":
    main()
