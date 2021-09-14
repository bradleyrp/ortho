# makefile shortcuts
.PHONY: develop install check clean remove docs readdocs
NAME = ortho
develop:
	pip install -e '.[docs,cli]'
install:
	pip install '.[docs,cli]'
check:
	python -c 'import ${NAME}'
clean:
	rm -rf ./${NAME}.egg-info
	rm -rf build dist
	find . -name __pycache__ -type d -exec rm -rf {} \; || :
	find . -name "*.pyc" -type f -exec rm {} \; || :
remove:
	pip uninstall ${NAME} -y
docs:
	make -C docs html -b coverage
	cat docs/build/coverage/python.txt
readdocs:
	open docs/build/html/index.html
