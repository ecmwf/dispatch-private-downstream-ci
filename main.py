import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone

import requests

# Constants
GITHUB_BASE_URL = "https://api.github.com"


class WF_Conclusions:
    SUCCESS = "success"
    FAILURE = "failure"


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


def warning(msg: str) -> None:
    print(f"::warning::{msg}")


@group("Inputs")
def get_args() -> dict:
    parser = argparse.ArgumentParser()
    parser.add_argument("token", type=str)
    parser.add_argument("github_token", type=str)
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
    guid = str(uuid.uuid4())
    data = {
        "event_type": event_type,
        "client_payload": {
            "id": guid,
            "inputs": payload,
        },
    }
    print(f"==> POST: {url}\n", data)
    response = session.post(url, data=json.dumps(data))

    if response.status_code == requests.codes.no_content:
        print(f"Workflow triggered: {guid}")
        return guid
    else:
        error(f"==> {response.status_code}: Error dispatching workflow!")
        print(response.json())
        sys.exit(1)


def check_workflow_id(session: requests.Session, url: str) -> str:
    """
    Returns name of second step in first job,
    i.e. where we store our wf GUID
    """

    response = session.get(url)

    if response.status_code != requests.codes.ok:
        error(f"{response.status_code}: Failed GET {url}")
        print(response.json())
        sys.exit(1)

    data = response.json().get("jobs", [])
    steps = data[0].get("steps")
    if len(steps) < 2:
        return ""
    guid = steps[1].get("name")  # Our randomly generated GUID
    return guid


@group("Get workflow for ID")
def get_workflow_run(
    session: requests.Session, guid: str, owner: str, repo: str
) -> dict:
    # get T minus 2 minutes in ISO format
    start_time = datetime.now()
    timestamp = datetime.now(tz=timezone.utc) - timedelta(minutes=2)
    timestamp_formatted = timestamp.isoformat(timespec="seconds")

    url = f"{GITHUB_BASE_URL}/repos/{owner}/{repo}/actions/runs"
    params = {
        "event": "repository_dispatch",
        "created": f">{timestamp_formatted}",
    }

    print(f"Polling API for WF {guid}")
    time.sleep(10)  # Allow the workflow to start
    while True:
        # Poll repository runs repeatedly
        response = session.get(url, params=params)
        print(f"==> GET: {response.url}")

        if response.status_code != requests.codes.ok:
            error(f"{response.status_code}: Failed GET request")
            print(response.json())
            sys.exit(1)

        data: dict = response.json()

        for run in data.get("workflow_runs"):
            if guid == check_workflow_id(session, run.get("jobs_url")):
                github_id = str(run.get("id"))
                print(f"GitHub ID for WF {guid}: {github_id}")
                return run

        if datetime.now() - start_time > timedelta(minutes=5):
            error("Failed getting workflow run for {guid}")
            sys.exit(1)
        time.sleep(10)


def get_workflow_run_conclusion(session: requests.Session, run: dict) -> dict:
    start_time = datetime.now()
    url = run.get("url")
    while True:
        response = session.get(url)

        if response.status_code != requests.codes.ok:
            error(f"{response.status_code}: Failed GET request {url}")
            print(response.json())
            sys.exit(1)

        data: dict = response.json()
        conclusion = data.get("conclusion")
        html_url = data.get("html_url")
        if conclusion == WF_Conclusions.SUCCESS:
            print("Workflow finished SUCCESSFULLY!")
            break

        if conclusion == WF_Conclusions.FAILURE:
            error("Workflow FAILED!")
            break

        if datetime.now() - start_time > timedelta(hours=1):
            error("Timeout: Workflow has not finished")
            print(html_url)
            sys.exit(1)

        time.sleep(10)

    print(html_url)
    return {
        "conclusion": conclusion,
        "run_url": html_url,
        "wf_name": run.get("name"),
    }


def get_pr_url() -> str:
    if (
        os.getenv("GITHUB_EVENT_NAME") != "pull_request"
        or not os.getenv("GITHUB_REF")
        or not os.getenv("GITHUB_REPOSITORY")
    ):
        return ""

    pr_number = (
        os.getenv("GITHUB_REF").removeprefix("refs/pull/").removesuffix("/merge")
    )
    owner, repo = os.getenv("GITHUB_REPOSITORY").split("/")

    pr_url = f"{GITHUB_BASE_URL}/repos/{owner}/{repo}/issues/{pr_number}/comments"

    return pr_url


def post_pr_comment(comment_body: str, session: requests.Session) -> None:

    pr_url = get_pr_url()
    data = {"body": comment_body}

    response = session.post(pr_url, data=json.dumps(data))

    if response.status_code != requests.codes.created:
        warning(
            f"==> {response.status_code}: Error posting comment to pull request"
            f"{pr_url}"
        )
        print(response.json())


def get_pr_comments(session: requests.Session) -> list:
    pr_url = get_pr_url()
    response = session.get(pr_url)

    if response.status_code != requests.codes.ok:
        warning(
            f"==> {response.status_code}: Error fetching list of PR comments {pr_url}"
        )
        print(response.json())
        return []

    return response.json()


def update_pr_comments(session: requests.Session, wf_result: dict):
    fail_msg = f"""Private downstream CI failed.
        Workflow name: {wf_result.get("wf_name")}
        View the logs at {wf_result.get("run_url")}."""

    success_msg = f"""Private downstream CI succeeded.
        Workflow name: {wf_result.get("wf_name")}
        View the logs at {wf_result.get("run_url")}."""

    if wf_result.get("conclusion") == WF_Conclusions.FAILURE:
        post_pr_comment(fail_msg, session)
        return

    comments_by_bot = list(
        filter(
            lambda o: o["user"]["login"] == "github-actions[bot]",
            get_pr_comments(session),
        )
    )

    # comment after success only if the WF previously failed
    for comment in comments_by_bot:
        if (
            f"Workflow name: {wf_result.get('wf_name')}" in comment["body"]
            and "failed" in comment["body"]
        ):
            post_pr_comment(success_msg, session)


def main():
    inputs = get_args()

    # Setup Github session auth
    session = requests.Session()
    session.headers = {"Authorization": f"token {inputs.get('token')}"}

    # Setup Github session with github-actions token
    actions_session = requests.Session()
    actions_session.headers = {"Authorization": f"token {inputs.get('github_token')}"}

    guid = dispatch_workflow(session, **inputs)
    workflow_run = get_workflow_run(
        session, guid, inputs.get("owner"), inputs.get("repo")
    )
    wf_result = get_workflow_run_conclusion(session, workflow_run)

    update_pr_comments(actions_session, wf_result)

    if wf_result.get("conclusion") == WF_Conclusions.FAILURE:
        sys.exit(1)


if __name__ == "__main__":
    main()
