SHELL := /bin/bash
PYTHON ?= $(shell if [ -x /opt/anaconda3/bin/python3 ]; then echo /opt/anaconda3/bin/python3; else command -v python3; fi)

.PHONY: all clean

all: ../output/manifest.csv

../output ../input:
	mkdir -p $@

../input/MMB_IRF_format_full.dta: ../../../data/build_mmb_analysis_dataset/output/MMB_IRF_format_full.dta | ../input
	ln -sf ../../../data/build_mmb_analysis_dataset/output/MMB_IRF_format_full.dta $@

../output/manifest.csv: make_output_cloud_graphs.py ../input/MMB_IRF_format_full.dta | ../output
	$(PYTHON) make_output_cloud_graphs.py

clean:
	rm -rf ../output/cloud_graphs ../output/manifest.csv ../output/.matplotlib
