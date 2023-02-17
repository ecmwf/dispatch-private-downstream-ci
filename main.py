def start_group(name: str) -> None:
    print(f"::group::{name}")


def end_group() -> None:
    print("::endgroup::")


def error(msg: str) -> None:
    print(f"::error::{msg}")


def debug(msg: str) -> None:
    print(f"::debug::{msg}")


def dispatch_workflow(owner: str, repo: str, event_type: str, payload: dict):
    pass


def main():
    # get args
    # dispatch wf with random id
    # poll api for wf with id (timeout)
    # poll api for wf status (timeout)
    # exit ok/ko, link to wf
    # if pr, comment link
    pass


if __name__ == "__main__":
    main()
