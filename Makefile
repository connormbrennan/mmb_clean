SHELL := /bin/bash
.RECIPEPREFIX := >

.PHONY: help tree clean

help:
> @echo ""
> @echo "Available targets:"
> @echo "  make tree   - show project tree if 'tree' is installed"
> @echo "  make clean  - remove common temporary files"
> @echo ""

tree:
> @if command -v tree >/dev/null 2>&1; then \
>   tree -a -I '.git|__pycache__|.ipynb_checkpoints' .; \
> else \
>   echo "Install 'tree' to use this target."; \
> fi

clean:
> @find . -name '*.log' -type f -delete
> @find . -name '*.aux' -type f -delete
> @find . -name '*.out' -type f -delete
> @find . -name '*.toc' -type f -delete
> @find . -name '.DS_Store' -type f -delete
