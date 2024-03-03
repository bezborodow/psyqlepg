.PHONY: all build clean publish test

all:

build:
	python3 -m build

publish:
	python3 -m twine upload --repository pypi dist/*

test:
	python -m unittest

clean:
	rm -fr dist
	rm -fr *.egg-info
