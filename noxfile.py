import os

import nox

os.environ.update({"PDM_IGNORE_SAVED_PYTHON": "1"})


@nox.session
def tests(session: nox.Session) -> None:
    session.run_always("pdm", "install", "-G", "tests", external=True)
    session.run("pytest", "-v", "tests/")


@nox.session
def lint(session: nox.Session) -> None:
    session.run_always("pdm", "install", "-G", "lint", external=True)
    session.run("ruff", "check", "--fix", "src/", "tests/")
    session.run("ruff", "format", "src/", "tests/")
