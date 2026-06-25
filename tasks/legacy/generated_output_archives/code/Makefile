SHELL := /bin/bash
PYTHON ?= $(shell if [ -x /opt/anaconda3/bin/python3 ]; then echo /opt/anaconda3/bin/python3; else command -v python3; fi)

.PHONY: all clean

all: ../output/generated_output_archives_manifest.txt

../output ../input:
	mkdir -p $@

../output/generated_output_archives_manifest.txt: copy_generated_output_archives.py ../../../../legacy/mmb_upgraded/bob ../../../../legacy/mmb_upgraded/cloud_graphs ../../../../legacy/mmb_upgraded/outlier_charts | ../output
	$(PYTHON) copy_generated_output_archives.py

clean:
	rm -rf ../output/bob ../output/cloud_graphs ../output/outlier_charts ../output/generated_output_archives_manifest.txt
