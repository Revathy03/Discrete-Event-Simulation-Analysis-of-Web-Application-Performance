CC = g++
CFLAGS = -Wall -Wextra -std=c++17 -Isrc
SRC_DIR = src
OBJ_DIR = obj

# Find all .cpp files in src and its subdirectories
SRCS = $(shell find $(SRC_DIR) -name "*.cpp")
OBJS = $(SRCS:$(SRC_DIR)/%.cpp=$(OBJ_DIR)/%.o)

TARGET = web_sim

all: $(TARGET) tandem

$(TARGET): $(OBJS)
	$(CC) $(CFLAGS) -o $@ $^

$(OBJ_DIR)/%.o: $(SRC_DIR)/%.cpp
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) -c $< -o $@

tandem:
	$(MAKE) -C tandem_queue

clean:
	rm -rf $(OBJ_DIR) $(TARGET)
	$(MAKE) -C tandem_queue clean
	rm -rf results/ final_results/
	rm -f tmp_config_*.txt tmp_cfg_*.txt

run: all
	@mkdir -p final_results/main_experiment final_results/what_if_analysis/baseline final_results/what_if_analysis/current
	python3 run_experiments.py
	python3 run_analysis.py
	@if [ -d what_if_analysis_v1_baseline ]; then \
		cp -r what_if_analysis_v1_baseline/* final_results/what_if_analysis/baseline/; \
		echo "Baseline what-if analysis included in final_results/what_if_analysis/baseline"; \
	fi
	cd tandem_queue && python3 verify_tandem.py
	@echo "\n--- All experiments completed. Results are organized in final_results/ ---"

.PHONY: all clean run tandem
