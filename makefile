# makefile shortcuts
.PHONY: develop install check clean remove
NAME = ortho
develop:
	pip install -e .
install:
	pip install .
check:
	python -c 'import ${NAME}'
clean:
	rm -rf ./${NAME}.egg-info
	rm -rf build dist
	find . -name __pycache__ -type d -exec rm -rf {} \; || :
	find . -name "*.pyc" -type f -exec rm {} \; || :
remove:
	pip uninstall ${NAME} -y