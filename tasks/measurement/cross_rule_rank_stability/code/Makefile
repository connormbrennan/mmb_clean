SHELL := /bin/bash
PYTHON ?= $(shell if [ -x /opt/anaconda3/bin/python3 ]; then echo /opt/anaconda3/bin/python3; else command -v python3; fi)

.PHONY: all clean FORCE
.NOTPARALLEL:

UPSTREAM_MMB_REG := ../../../data/build_mmb_analysis_dataset/output/MMB_reg_format.dta
STAMP := .build.stamp

OUTPUTS := \
	../output/cross_rule_rank_stability.csv \
	../output/cross_rule_rank_stability.tex \
	../output/cross_rule_rank_stability_heatmap.pdf \
	../output/cross_rule_rank_stability_heatmap.png \
	../output/cross_rule_rank_stability_heatmap_description.txt \
	../output/findings_note.md \
	../output/manifest.csv

all: $(OUTPUTS)

clean:
	mkdir -p ../input ../output
	rm -f $(OUTPUTS)
	rm -f $(STAMP)
	find ../input -mindepth 1 -maxdepth 1 -type l -exec unlink {} \;
	touch ../input/.gitkeep ../output/.gitkeep

FORCE:

$(UPSTREAM_MMB_REG): FORCE
	$(MAKE) --no-print-directory -C ../../../data/build_mmb_analysis_dataset
	test -f $@

../input/MMB_reg_format.dta: | ../input $(UPSTREAM_MMB_REG)
	ln -sfn $(UPSTREAM_MMB_REG) $@

$(STAMP): main.py ../input/MMB_reg_format.dta ../../../../config/params.yaml | ../output $(UPSTREAM_MMB_REG)
	$(PYTHON) main.py
	@for f in $(OUTPUTS); do test -f "$$f" || { echo "Missing $$f"; exit 1; }; done
	touch $(STAMP)

$(OUTPUTS): $(STAMP)
	@test -f $@ || { rm -f $(STAMP); $(MAKE) --no-print-directory $(STAMP); test -f $@; }

../input ../output:
	mkdir -p $@
