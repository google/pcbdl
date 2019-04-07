COVERAGE ?= python3 -m coverage
RUN_COVERAGE ?= $(COVERAGE) run -a --branch

.PHONY: test
test: RUN_TEST ?= $(RUN_COVERAGE)
test:
	$(RUN_TEST) test/base.py -v
	$(RUN_TEST) test/small_parts.py -v

.PHONY: show-coverage
show-coverage:
	$(COVERAGE) report -m
	$(COVERAGE) html
	@xdg-open htmlcov/index.html

.PHONY: clean-coverage
clean-coverage:
	-$(COVERAGE) erase
	-rm -Rf htmlcov

.PHONY: clean
clean: clean-coverage
