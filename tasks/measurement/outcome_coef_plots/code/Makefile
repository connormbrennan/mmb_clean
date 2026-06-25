SHELL := /bin/bash
PYTHON ?= $(shell if [ -x /opt/anaconda3/bin/python3 ]; then echo /opt/anaconda3/bin/python3; else command -v python3; fi)

.PHONY: all clean

all: ../output/coef_plots_outcomes.zip

../output ../input:
	mkdir -p $@

../input/MMB_reg_format.dta: ../../../data/build_mmb_analysis_dataset/output/MMB_reg_format.dta | ../input
	ln -sf ../../../data/build_mmb_analysis_dataset/output/MMB_reg_format.dta $@

../output/coef_plots_outcomes.zip: make_outcome_coef_plots.py ../input/MMB_reg_format.dta | ../output
	$(PYTHON) make_outcome_coef_plots.py

clean:
	rm -rf ../output/coef_plots_outcomes ../output/coef_plots_outcomes.zip ../output/coef_plots_outcomes_description.txt ../output/manifest.csv
