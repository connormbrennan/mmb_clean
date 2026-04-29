SHELL := /bin/bash
PYTHON ?= $(shell if [ -x /opt/anaconda3/bin/python3 ]; then echo /opt/anaconda3/bin/python3; else command -v python3; fi)

.PHONY: all clean

all: ../output/legacy_exact_manifest.txt

../output ../input:
	mkdir -p $@

../output/legacy_exact_manifest.txt: reproduce_legacy_outputs.py ../../../legacy/mmb_upgraded | ../output
	$(PYTHON) reproduce_legacy_outputs.py

clean:
	rm -rf ../output/legacy_exact ../output/legacy_exact_manifest.txt
