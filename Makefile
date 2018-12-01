COVERAGE = coverage3 run --branch

.PHONY: test
test:
	$(COVERAGE) test/base.py -v

.PHONY: show-coverage
show-coverage:
	coverage3 report -m
	coverage3 html
	@xdg-open htmlcov/index.html

.PHONY: clean-coverage
clean-coverage:
	coverage3 erase
	-rm -Rf htmlcov

.PHONY: clean
clean: clean-coverage
