.PHONY: clean delete api all

clean: ## Clean up all build outputs
	./cleanup.sh

delete: ## delete up all generated docs
	./cleanup.sh --outputs

api: delete ## Generate an API-Reference website from source code at /docs/API-Reference
	./build_api_ref.sh; \
	./cleanup.sh


all: api ## Generate a website containing the API reference as well as other markdown docs
	./build_full_html.sh; \
	./cleanup.sh

# ----------------------------
# Help
# ----------------------------
.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

