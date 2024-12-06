lint:
	ruff check

reformat:
	ruff check --select I --fix
	ruff format
