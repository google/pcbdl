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
	@echo "	make test"
	@echo "	make show-coverage"
	@echo "	make gh-pages-examples"
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

.PHONY: gh-pages-examples
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
	$(RUN_TEST) test/spice.py -v

.PHONY: show-coverage
show-coverage:
	$(COVERAGE) report -m
	$(COVERAGE) html
	@xdg-open htmlcov/index.html

.PHONY: clean-coverage
clean-coverage:
	-$(COVERAGE) erase
	$(RM) -R htmlcov


.PHONY: clean
clean: clean-coverage clean-gh-pages-examples
