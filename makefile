NAME = ortho
.PHONY: develop install check clean remove docs readdocs test
all:
develop: venv
	source venv/bin/activate && pip install -e '.[all]'
install: venv
	source venv/bin/activate && pip install '.[all]'
check:
	python -c 'import ${NAME}'
# via https://stackoverflow.com/a/74776006
venv:
	@read -p "question: no linked venv. should we make one? [y/N] " ans && \
	ans=$${ans:-N} ; \
    if [ $${ans} = y ] || [ $${ans} = Y ]; then \
    	python3 -m venv venv ; \
		echo "status: installed a local environment" ; \
    else \
        echo "status: aborting" ; exit 1 ; \
    fi
clean:
	unlink venv || :
	rm -rf ./venv
	rm -rf ./${NAME}.egg-info
	rm -rf build dist
	find . -name __pycache__ -type d -exec rm -rf {} \; || :
	find . -name "*.pyc" -type f -exec rm {} \; || :
remove:
	source venv/bin/activate && pip uninstall ${NAME} -y
docs:
	make -C docs html -b coverage
	cat docs/build/coverage/python.txt
readdocs:
	open docs/build/html/index.html
test:
	source venv/bin/activate && python -m unittest
