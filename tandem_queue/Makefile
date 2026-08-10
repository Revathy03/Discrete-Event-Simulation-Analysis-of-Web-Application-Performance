CC = g++
CFLAGS = -Wall -Wextra -std=c++17 -Isrc
SRC_DIR = src
OBJ_DIR = obj

# Find all .cpp files in src and its subdirectories
SRCS = $(shell find $(SRC_DIR) -name "*.cpp")
OBJS = $(SRCS:$(SRC_DIR)/%.cpp=$(OBJ_DIR)/%.o)

TARGET = web_sim

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CC) $(CFLAGS) -o $@ $^

$(OBJ_DIR)/%.o: $(SRC_DIR)/%.cpp
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -rf $(OBJ_DIR) $(TARGET)

run: $(TARGET)
	python3 run_experiments.py
	python3 plot_results.py

.PHONY: all clean run
