SHELL := /bin/bash
PYTHON ?= $(shell if [ -x /opt/anaconda3/bin/python3 ]; then echo /opt/anaconda3/bin/python3; else command -v python3; fi)

.PHONY: all build clean FORCE
.NOTPARALLEL:

UPSTREAM_MMB_REG := ../../../data/build_mmb_analysis_dataset/output/MMB_reg_format.dta

PRIMARY_OUTPUT := ../output/summarystats/table3_summary_stats.tex

OUTPUTS := \
	../output/manifest.csv \
	$(PRIMARY_OUTPUT) \
	../output/summarystats/table3_summary_stats.csv \
	../output/summarystats/table4_elasticity_stats.tex \
	../output/summarystats/table4_elasticity_stats.csv \
	../output/summarystats/table5_timing_stats.tex \
	../output/summarystats/table5_timing_stats.csv \
	../output/summarystats/outcome_summary_stats_by_rule.csv \
	../output/summarystats/texresults_outcomevars_stats_output.txt \
	../output/summarystats/piq_timing_max_rules_timing_hist.pdf \
	../output/summarystats/piq_timing_max_rules_timing_hist_description.txt \
	../output/summarystats/piq_timing_max_types_timing_hist.pdf \
	../output/summarystats/piq_timing_max_types_timing_hist_description.txt \
	../output/summarystats/y_timing_max_rules_timing_hist.pdf \
	../output/summarystats/y_timing_max_rules_timing_hist_description.txt \
	../output/summarystats/y_timing_max_types_timing_hist.pdf \
	../output/summarystats/y_timing_max_types_timing_hist_description.txt \
	../output/summarystats/rrate_timing_min_rules_timing_hist.pdf \
	../output/summarystats/rrate_timing_min_rules_timing_hist_description.txt \
	../output/summarystats/rrate_timing_min_types_timing_hist.pdf \
	../output/summarystats/rrate_timing_min_types_timing_hist_description.txt \
	../output/summarystats/irate_timing_min_rules_timing_hist.pdf \
	../output/summarystats/irate_timing_min_rules_timing_hist_description.txt \
	../output/summarystats/irate_timing_min_types_timing_hist.pdf \
	../output/summarystats/irate_timing_min_types_timing_hist_description.txt

all: build

clean:
	rm -f $(OUTPUTS)
	rm -rf ../output/summarystats
	rm -f ../output/exact_manifest.txt
	find ../input -mindepth 1 -maxdepth 1 -type l -exec unlink {} \;
	touch ../input/.gitkeep ../output/.gitkeep

FORCE:

upstream_mmb_analysis_dataset: FORCE
	$(MAKE) --no-print-directory -C ../../../data/build_mmb_analysis_dataset
	test -f $(UPSTREAM_MMB_REG)

$(UPSTREAM_MMB_REG): | upstream_mmb_analysis_dataset
	test -f $@

../input/MMB_reg_format.dta: | ../input upstream_mmb_analysis_dataset
	ln -sfn $(UPSTREAM_MMB_REG) $@

build: make_summary_stats.py ../input/MMB_reg_format.dta $(UPSTREAM_MMB_REG) ../../../../config/params.yaml | ../output upstream_mmb_analysis_dataset
	$(PYTHON) make_summary_stats.py
	@for f in $(OUTPUTS); do test -f "$$f" || exit 1; done

../input ../output:
	mkdir -p $@
