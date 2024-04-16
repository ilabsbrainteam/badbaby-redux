.PHONY: rsync-local rsync-server clean docs

.DEFAULT_GOAL := docs

# GET DATA
rsync-local:
	sudo bash rsync-data-from-local-untitled-drive.sh

rsync-server:
	bash rsync-data-from-server.sh


# DECIDE WHICH DATA TO KEEP
files-from-local.yaml: rsync-local
	python select-files-from-local.py

files-from-server.yaml: rsync-server
	python select-files-from-server.py


# COMBINE THE TWO DATA SOURCES
qc/log-of-hardlinking.txt: files-from-local.yaml files-from-server.yaml
	python make-hardlinks.py


# DOCUMENT WHAT DATA WE HAVE
qc/files-in-data.csv qc/erm-missing-from-data.csv: qc/log-of-hardlinking.txt
	python catalog-data-completeness.py combined
# also generates:
# - qc/summary-of-combined-data.txt
# - qc/unexpected-files-of-combined-data.txt

qc/files-in-local-data.csv: qc/log-of-hardlinking.txt
	python catalog-data-completeness.py local
# also generates:
# - qc/erm-missing-from-local-data.csv
# - qc/summary-of-local-data.txt
# - qc/unexpected-files-of-local-data.txt


# FIND SURROGATE ERMS
qc/erm-surrogates.csv: qc/erm-missing-from-data.csv
	python find-surrogate-erms.py
# also generates:
# - qc/log-of-surrogate-erms.txt
# - qc/erm-missing-dates.txt

qc/summary-after-linking-erms.txt: qc/erm-surrogates.csv
	python link-surrogate-erms.py
	python catalog-data-completeness.py erm
# also generates:
# - qc/unexpected-files-after-linking-erms.txt


# GENERATE LIST OF MISSING FILES
qc/files-missing.txt: qc/files-in-data.csv
	python list-missing-filenames.py


# UTILS
clean:
	rm -rf /storage/badbaby-redux/data/bad_*
	rm -f qc/*

docs:
	@echo "No default recipe."

all: qc/files-missing.txt qc/summary-after-linking-erms.txt qc/files-in-local-data.csv
	@echo "Regenerated everything. Check:"; \
	echo "    qc/summary-after-linking-erms.txt"; \
	echo "    qc/unexpected-files-after-linking-erms.txt"; \
	echo "    qc/missing-files.txt"; \
	echo "    qc/log-of-hardlinking.txt"
