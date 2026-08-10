import os
import glob
from PIL import Image

def combine_images_horizontally():
    results_dir = "results"
    
    if not os.path.exists(results_dir):
        print(f"Error: Directory {results_dir} not found.")
        return

    # Find all think_time_* directories
    think_time_dirs = [d for d in os.listdir(results_dir) if os.path.isdir(os.path.join(results_dir, d)) and d.startswith("think_time_")]
    
    # Expected service time distributions to combine
    # We can sort them to have a consistent order
    service_time_dirs = ["service_time_CONSTANT", "service_time_EXPONENTIAL", "service_time_UNIFORM"]

    for think_time_dir in think_time_dirs:
        think_time_path = os.path.join(results_dir, think_time_dir)
        
        # Determine the base directory to find all possible graph types
        # We will use the first available service_time_dir as the reference for graph types
        reference_dir = os.path.join(think_time_path, service_time_dirs[0])
        
        if not os.path.exists(reference_dir):
            print(f"Skipping {think_time_dir}, {reference_dir} not found.")
            continue
            
        # Output directory for combined images
        output_dir = os.path.join(think_time_path, "combined_plots")
        os.makedirs(output_dir, exist_ok=True)
        
        # Get all png files in the reference directory
        graph_types = [f for f in os.listdir(reference_dir) if f.endswith(".png")]
        
        print(f"\nProcessing {think_time_dir}...")
        
        for graph_type in graph_types:
            images = []
            valid = True
            
            # Load the same graph type for all service time distributions
            for st_dir in service_time_dirs:
                img_path = os.path.join(think_time_path, st_dir, graph_type)
                if os.path.exists(img_path):
                    try:
                        img = Image.open(img_path)
                        images.append(img)
                    except Exception as e:
                        print(f"  Error loading {img_path}: {e}")
                        valid = False
                        break
                else:
                    print(f"  Missing {img_path}")
                    valid = False
                    break
            
            if not valid or not images:
                continue
                
            # Calculate total width and max height for the combined image
            widths, heights = zip(*(i.size for i in images))
            total_width = sum(widths)
            max_height = max(heights)
            
            # Create a new white background image
            combined_img = Image.new('RGB', (total_width, max_height), color='white')
            
            # Paste individual images side by side
            x_offset = 0
            for img in images:
                combined_img.paste(img, (x_offset, 0))
                x_offset += img.size[0]
                
            # Save the combined image
            output_path = os.path.join(output_dir, graph_type)
            combined_img.save(output_path)
            print(f"  Saved combined {graph_type} to {output_path}")

            # Delete source images to save space as requested by user
            for st_dir in service_time_dirs:
                img_path = os.path.join(think_time_path, st_dir, graph_type)
                if os.path.exists(img_path):
                    os.remove(img_path)
                    # print(f"    Deleted source: {img_path}")


if __name__ == "__main__":
    print("Combining images...")
    combine_images_horizontally()
    print("Done!")
