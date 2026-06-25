SHELL := /bin/bash
PYTHON ?= $(shell if [ -x /opt/anaconda3/bin/python3 ]; then echo /opt/anaconda3/bin/python3; else command -v python3; fi)

.PHONY: all clean

all: ../output/artifact_inventory.txt

../output ../input:
	mkdir -p $@

../output/artifact_inventory.txt: inventory_legacy_artifacts.py ../../../../legacy/mmb_upgraded | ../output
	$(PYTHON) inventory_legacy_artifacts.py

clean:
	rm -f ../output/artifact_inventory.txt
