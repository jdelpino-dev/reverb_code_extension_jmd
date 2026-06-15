# hiring-code-python

Repo for coding interviews. Interviewer details are [in Confluence](https://reverb.atlassian.net/wiki/spaces/ENG/pages/3833233418).

## Description

A Flask web application that displays gear categories and product listings from the [Reverb API](https://www.reverb-api.com/).

## Getting started

```bash
uv sync --dev
uv run flask --app app run --debug
```

Visit http://localhost:5000

## Testing

```bash
uv run pytest
```

## Linting

```bash
uv run ruff check .
uv run ruff format .
```
