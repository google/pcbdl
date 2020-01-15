.DEFAULT: usage
.PHONY: usage
usage:
	@echo "This makefile could be used for automating pcbdl exporting:"
	@echo "	make yourcircuit.html"
	@echo "	make yourcircuit.svg"
	@echo "	make yourcircuit.allegro_third_party/"
	@echo "	make yourcircuit.shell"
	@echo
	@echo "yourcircuit could be stored anywhere, could be an absolute path."
	@echo "If the circuit is outside the pcbdl folder (suggested), make needs a -f flag to point it back to this file:"
	@echo "	make -f /path/to/pcbdl/Makefile /another/path/to/yourcircuit.html"
	@echo
	@echo
	@echo "Other pcbdl project centric options:"
	@echo "	make doc"
	@echo "	make test"
	@echo "	make show-coverage"
	@echo "	make gh-pages"
	@echo "	make clean"


EXECUTE_SCHEMATIC = cd $(dir $<); python3 $2 -c "from $(basename $(notdir $<)) import *; $1"
EXECUTE_SCHEMATIC_TO_FILE = $(call EXECUTE_SCHEMATIC, output=open('$(@F)', 'w'); output.write($1); output.close(), $2)

# we shouldn't care if refdes mapping files are missing, so here's a dummy rule:
%.refdes_mapping: %.py ;

%.allegro_third_party/: %.py %.refdes_mapping
	$(call EXECUTE_SCHEMATIC,generate_netlist('$(basename $(<F))'))

%.html: %.py %.refdes_mapping
	$(call EXECUTE_SCHEMATIC_TO_FILE,generate_html(include_svg=True))

%.svg: %.py %.refdes_mapping # Big schematic all in one page
	$(call EXECUTE_SCHEMATIC_TO_FILE,list(generate_svg())[0])

%.i2c.svg: %.py %.refdes_mapping
	$(call EXECUTE_SCHEMATIC_TO_FILE,list(generate_svg(net_regex='.*(SDA|SCL).*', airwires=0))[0])

%.power.svg: %.py %.refdes_mapping
	$(call EXECUTE_SCHEMATIC_TO_FILE,list(generate_svg(net_regex='.*(PP|GND|VIN|VBUS).*'))[0])

.PHONY: %.shell
%.shell: %.py %.refdes_mapping
	$(call EXECUTE_SCHEMATIC,,-i)

SERVO_MICRO_EXAMPLE_OUTPUTS := $(shell echo examples/servo_micro.{svg,html,allegro_third_party/} examples/servo_micro.{i2c,power}.svg)

.PHONY: gh-pages
gh-pages-examples: $(SERVO_MICRO_EXAMPLE_OUTPUTS) ;

clean-gh-pages-examples:
	$(RM) -R $(SERVO_MICRO_EXAMPLE_OUTPUTS)

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
	$(RM) -R htmlcov

.PHONY: doc
doc: doc/_build/html
doc/_build/html: .
	cd doc/ && $(MAKE) html

.PHONY: clean-doc
clean-doc:
	$(RM) -R doc/_build

.PHONY: gh-pages
gh-pages: doc gh-pages-examples

.PHONY: refresh-gh-pages
refresh-gh-pages:
	git checkout gh-pages
	git reset --hard master # track the master branch

	$(MAKE) clean
	$(MAKE) gh-pages
	git add -f doc/*
	git add -f $(SERVO_MICRO_EXAMPLE_OUTPUTS)

	touch .nojekyll # Make sure we can show index.html from docs/
	git add .nojekyll

	git commit -s -m "Ran make refresh-gh-pages"
	git checkout -

.PHONY: clean
clean: clean-coverage clean-gh-pages-examples clean-doc
