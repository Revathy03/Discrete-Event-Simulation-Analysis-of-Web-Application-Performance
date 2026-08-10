#!/bin/bash

# Configuration
DES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT_DIR="$(dirname "$DES_DIR")"
VENV_PATH="$PARENT_DIR/.venv"
ZIP_NAME="25M0768_25M2138_des.zip"
ZIP_PATH="$PARENT_DIR/$ZIP_NAME"

echo "Step 1: Building simulator..."
make

echo -e "\nStep 2: Activating Virtual Environment..."
if [ -d "$VENV_PATH" ]; then
    source "$VENV_PATH/bin/activate"
    echo "Activated venv at $VENV_PATH"
else
    echo "Warning: .venv not found at $VENV_PATH. Using system python."
fi

echo -e "\nStep 3: Ensuring dependencies are installed..."
pip install xlsxwriter > /dev/null 2>&1

echo -e "\nStep 4: Regenerating plots..."
scripts=("plot_results.py" "run_analysis.py" "create_comparison_tables.py" "combine_plots.py")
for script in "${scripts[@]}"; do
    if [ -f "$DES_DIR/$script" ]; then
        echo "Running $script..."
        python "$DES_DIR/$script"
    else
        echo "Warning: $script not found."
    fi
done

echo -e "\nStep 5: Cleaning up unnecessary files..."
# Remove macOS hidden files and Python cache
find "$DES_DIR" -name ".DS_Store" -type f -delete
find "$DES_DIR" -name "__pycache__" -type d -exec rm -rf {} +

to_delete=("mm1simcode" "obj" "web_sim" "test_rng")
for item in "${to_delete[@]}"; do
    item_path="$DES_DIR/$item"
    if [ -e "$item_path" ]; then
        rm -rf "$item_path"
        echo "Deleted: $item"
    fi
done

echo -e "\nStep 6: Creating ZIP file..."
if [ -f "$ZIP_PATH" ]; then
    rm "$ZIP_PATH"
    echo "Removed existing $ZIP_NAME"
fi

cd "$PARENT_DIR"
zip -r "$ZIP_NAME" des -x '**/.*' -x '**/__MACOSX'

if [ -f "$ZIP_PATH" ]; then
    SIZE=$(ls -lh "$ZIP_PATH" | awk '{print $5}')
    echo -e "\nSuccessfully created $ZIP_NAME ($SIZE)"
else
    echo "Failed to create ZIP file."
fi

# Deactivate venv if it was activated
if [ -n "$VIRTUAL_ENV" ]; then
    deactivate
fi
