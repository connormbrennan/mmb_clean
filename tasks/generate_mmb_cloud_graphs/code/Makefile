SHELL := /bin/bash
PYTHON ?= $(shell if [ -x /opt/anaconda3/bin/python3 ]; then echo /opt/anaconda3/bin/python3; else command -v python3; fi)

.PHONY: all clean

FIGURE_BASES = \
	piq_all y_all irate_all rrate_all \
	piq_inertial_taylor y_inertial_taylor irate_inertial_taylor rrate_inertial_taylor \
	piq_taylor y_taylor irate_taylor rrate_taylor \
	piq_growth y_growth irate_growth rrate_growth \
	piq_estimated y_estimated irate_estimated rrate_estimated \
	piq_calibrated y_calibrated irate_calibrated rrate_calibrated \
	piq_estimated_inertial_taylor y_estimated_inertial_taylor irate_estimated_inertial_taylor rrate_estimated_inertial_taylor \
	piq_estimated_taylor y_estimated_taylor irate_estimated_taylor rrate_estimated_taylor \
	piq_estimated_growth y_estimated_growth irate_estimated_growth rrate_estimated_growth \
	piq_calibrated_inertial_taylor y_calibrated_inertial_taylor irate_calibrated_inertial_taylor rrate_calibrated_inertial_taylor \
	piq_calibrated_taylor y_calibrated_taylor irate_calibrated_taylor rrate_calibrated_taylor \
	piq_calibrated_growth y_calibrated_growth irate_calibrated_growth rrate_calibrated_growth

FIGURES = $(addprefix ../output/,$(addsuffix .pdf,$(FIGURE_BASES)))
DESCRIPTIONS = $(addprefix ../output/,$(addsuffix _description.txt,$(FIGURE_BASES)))
OUTPUTS = $(FIGURES) $(DESCRIPTIONS) ../output/cloud_graphs_manifest.txt

all: $(OUTPUTS)

../input ../output:
	mkdir -p $@

../input/MMB_IRF_format_full.dta: ../../build_mmb_analysis_dataset/output/MMB_IRF_format_full.dta | ../input
	ln -s ../../build_mmb_analysis_dataset/output/MMB_IRF_format_full.dta $@

$(OUTPUTS): generate_cloud_graphs.py ../input/MMB_IRF_format_full.dta | ../output
	$(PYTHON) generate_cloud_graphs.py

clean:
	rm -f $(OUTPUTS)
	rm -rf ../output/.matplotlib
	find ../input -mindepth 1 -maxdepth 1 -type l -exec unlink {} \;
