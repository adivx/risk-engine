.PHONY: install test chart clean

install:
	python -m pip install -e .

test:
	python -m unittest discover -s tests -v

chart:
	risk-engine chart --out drawdown.svg

clean:
	rm -rf build dist *.egg-info __pycache__
