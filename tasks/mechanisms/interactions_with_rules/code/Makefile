SHELL := /bin/bash
PYTHON ?= $(shell if [ -x /opt/anaconda3/bin/python3 ]; then echo /opt/anaconda3/bin/python3; else command -v python3; fi)

.PHONY: all clean

all: ../output/manifest.csv

../output ../input:
	mkdir -p $@

../input/MMB_reg_format.dta: ../../../data/build_mmb_analysis_dataset/output/MMB_reg_format.dta | ../input
	ln -sf ../../../data/build_mmb_analysis_dataset/output/MMB_reg_format.dta $@

../output/manifest.csv: make_interactions_with_rules.py ../input/MMB_reg_format.dta | ../output
	$(PYTHON) make_interactions_with_rules.py

clean:
	rm -rf ../output/interactions_with_rules ../output/manifest.csv
