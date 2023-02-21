# Trigger private downstream CI

Github action to trigger workflows using repository dispatch event.

## Usage

See [action.yml](action.yml)

```yaml
steps:
  - uses: ecmwf-actions/dispatch-private-downstream-ci@main
    with:
      owner: owner
      repository: repo
      event_type: my-custom-event
      payload: '{"input1": "foo"}'
```

Action creates a `repository_dispatch` event in target repository. Workflow is specified by `event_type`. The first step of the first job in target workflow must be the following:

```yaml
steps:
  - name: ${{ github.event.client_payload.id }}
    run: ...
```

This is necessary to identify the triggered workflow and to watch for the workflow conclusion.
