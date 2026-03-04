# PulseAnalytics - the commands you actually run.
#
#   make setup        install dependencies into a virtualenv
#   make data         generate two years of synthetic history
#   make etl          build bronze -> silver -> star schema -> gold marts
#   make analytics    run every model, write reports/insight_report.md
#   make dashboard    open the Streamlit app
#   make stream       produce and consume live events (two terminals)
#   make test         run the test suite
#   make all          data + etl + analytics, from nothing
#
# Windows without make: every recipe is a one-line python command - run it
# directly, or use scripts/run_demo.py which does the whole sequence.

PYTHON ?= python
PRESET ?= small

.PHONY: setup data etl analytics quality dashboard api stream produce consume \
        test lint clean all docker-up docker-down powerbi

setup:
	$(PYTHON) -m venv .venv
	.venv/bin/pip install -U pip || .venv/Scripts/pip install -U pip
	.venv/bin/pip install -r requirements.txt || .venv/Scripts/pip install -r requirements.txt
	@echo "Activate with: source .venv/bin/activate  (Windows: .venv\Scripts\activate)"

data:
	$(PYTHON) data-generator/generate_data.py --preset $(PRESET)

etl:
	$(PYTHON) -m etl.pipeline --full-refresh

quality:
	$(PYTHON) -m etl.pipeline --quality-only --fail-on-error

analytics:
	$(PYTHON) -m analytics.run_analytics

dashboard:
	$(PYTHON) -m streamlit run dashboards/streamlit/app.py

api:
	$(PYTHON) -m uvicorn streaming.processors.realtime_api:app --reload --port 8000

# One-shot: 45 minutes of history so the live page is never empty.
stream:
	$(PYTHON) -m streaming.producer.event_producer --backfill-minutes 45
	$(PYTHON) -m streaming.consumer.stream_consumer --duration 10 --from-start

produce:
	$(PYTHON) -m streaming.producer.event_producer --rate 8 --duration 0

consume:
	$(PYTHON) -m streaming.consumer.stream_consumer --duration 0

powerbi:
	$(PYTHON) dashboards/powerbi/export_for_powerbi.py

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m compileall -q pulse etl streaming analytics dashboards tests

all: data etl analytics
	@echo "Done. Run 'make dashboard' to look at it."

docker-up:
	docker compose up -d postgres redpanda console

docker-down:
	docker compose down

clean:
	rm -rf data/raw/*.csv data/raw/_manifest.json data/warehouse/*.duckdb* \
	       data/stream/* data/exports/* .pytest_warehouse .pytest_cache reports/*.md
	@echo "Regenerate with: make all"
