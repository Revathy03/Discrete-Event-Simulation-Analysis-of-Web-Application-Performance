#include "simulation/Simulation.h"
#include <iostream>
#include <vector>
#include <iomanip>
#include <fstream>
#include <string>
#include <sstream> // Required for std::stringstream

#include <filesystem>

// runs a single simulation experiment with the given parameters and distributions
void run_experiment(int num_users, int num_servers, int num_cores, int threads_per_core, 
                    double ctx_overhead, double end_time, double warmup, 
                    double mean_think, double mean_service, double timeout,
                    double time_slice, int max_queue_size,
                    int num_runs, DistributionType s_dist, DistributionType t_dist,
                    const std::string& s_dist_name, const std::string& t_dist_name,
                    const std::string& output_base_dir, LBPolicy lb_policy,
                    double thermal_threshold = 75.0, double throttle_factor = 1.0) {
    
    std::vector<double> response_times;
    double total_throughput = 0;
    double total_goodput = 0;
    double total_badput = 0;
    double total_drop_rate = 0;
    double total_utilization = 0;
    double total_max_temp = 0;

    // run the simulation multiple times to compute a confidence interval for metrics
    for (int r = 0; r < num_runs; ++r) {
        Simulation sim(num_users, num_servers, num_cores, threads_per_core, ctx_overhead, end_time, warmup, 
                       mean_think, mean_service, timeout, time_slice, max_queue_size,
                       static_cast<unsigned int>(42 + r), s_dist, t_dist, lb_policy,
                       thermal_threshold, throttle_factor);
        sim.initialize();
        sim.run();

        response_times.push_back(sim.metrics.compute_avg_response_time());
        total_throughput += sim.metrics.compute_throughput();
        total_goodput += sim.metrics.compute_goodput();
        total_badput += sim.metrics.compute_badput();
        total_drop_rate += sim.metrics.compute_drop_rate();
        
        double sim_util = 0;
        double max_server_temp = 0;
        for (auto s : sim.servers) {
            sim_util += s->get_avg_core_utilization(sim.metrics.simulation_time);
            if (s->max_observed_temp > max_server_temp) max_server_temp = s->max_observed_temp;
        }
        total_utilization += (sim_util / num_servers);
        total_max_temp += max_server_temp;
    }

    Metrics::ConfidenceInterval ci = Metrics::compute_confidence_interval(response_times);

    std::cout << num_users << " | ";
    std::cout << ci.mean << " +/- " << ci.half_width << " | ";
    std::cout << total_throughput / num_runs << " | ";
    std::cout << total_goodput / num_runs << " | ";
    std::cout << total_badput / num_runs << " | ";
    std::cout << total_drop_rate / num_runs << " | ";
    std::cout << total_utilization / num_runs << " | ";
    std::cout << total_max_temp / num_runs << std::endl;

    // Output to CSV in distribution-specific directory
    // store the final aggregated results per experiment for plotting and analysis
    std::string dir_path = output_base_dir + "/think_time_" + t_dist_name + "/service_time_" + s_dist_name;
    std::filesystem::create_directories(dir_path);
    std::string file_path = dir_path + "/des_results.csv";
    
    std::ofstream csv(file_path, std::ios::app);
    if (csv.is_open()) {
        csv << num_users << "," 
            << ci.mean << "," 
            << ci.half_width << ","
            << total_throughput / num_runs << "," 
            << total_goodput / num_runs << ","
            << total_badput / num_runs << "," 
            << total_drop_rate / num_runs << ","
            << total_utilization / num_runs << ","
            << total_max_temp / num_runs << "\n";
        csv.close();
    }
}

// configuration object to hold all the tunable parameters for the simulation
struct Config {
    int cores = 1;
    int threads_per_core = 1;
    double ctx_overhead = 0.0012;
    double sim_time = 1000.0;
    double warmup = 100.0;
    double mean_think = 7.152;
    double mean_service = 0.048;
    double timeout = 10.0;
    double time_slice = 1.0;
    int max_queue_size = -1;
    int num_runs = 10;
    std::string output_dir = "results";
    DistributionType service_dist = DistributionType::EXPONENTIAL;
    DistributionType think_dist = DistributionType::EXPONENTIAL;
    std::vector<int> user_counts = {10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150, 160, 170, 180, 190, 200, 210, 220, 230};
    int num_servers = 1;
    LBPolicy lb_policy = LBPolicy::ROUND_ROBIN;
    double thermal_threshold = 75.0;
    double throttle_factor = 0.5;
};

// reads configuration from a text file, allowing user to tweak params without recompiling
Config load_config(const std::string& filename) {
    Config config;
    std::ifstream file(filename);
    if (!file.is_open()) {
        std::cerr << "Warning: Could not open " << filename << ". Using default values." << std::endl;
        return config;
    }

    std::string line;
    while (std::getline(file, line)) {
        if (line.empty() || line[0] == '#') continue;

        auto delimiterPos = line.find('=');
        if (delimiterPos == std::string::npos) continue;

        std::string name = line.substr(0, delimiterPos);
        std::string value = line.substr(delimiterPos + 1);

        if (name == "cores") config.cores = std::stoi(value);
        else if (name == "threads_per_core") config.threads_per_core = std::stoi(value);
        else if (name == "ctx_overhead") config.ctx_overhead = std::stod(value);
        else if (name == "sim_time") config.sim_time = std::stod(value);
        else if (name == "warmup") config.warmup = std::stod(value);
        else if (name == "mean_think") config.mean_think = std::stod(value);
        else if (name == "mean_service") config.mean_service = std::stod(value);
        else if (name == "timeout") config.timeout = std::stod(value);
        else if (name == "time_slice") config.time_slice = std::stod(value);
        else if (name == "max_queue_size") config.max_queue_size = std::stoi(value);
        else if (name == "num_runs") config.num_runs = std::stoi(value);
        else if (name == "output_dir") config.output_dir = value;
        else if (name == "service_distribution") {
            if (value == "CONSTANT") config.service_dist = DistributionType::CONSTANT;
            else if (value == "UNIFORM") config.service_dist = DistributionType::UNIFORM;
            else if (value == "EXPONENTIAL") config.service_dist = DistributionType::EXPONENTIAL;
        } else if (name == "think_distribution") {
            if (value == "CONSTANT") config.think_dist = DistributionType::CONSTANT;
            else if (value == "UNIFORM") config.think_dist = DistributionType::UNIFORM;
            else if (value == "EXPONENTIAL") config.think_dist = DistributionType::EXPONENTIAL;
        } else if (name == "user_counts") {
            config.user_counts.clear();
            std::stringstream ss(value);
            std::string item;
            while (std::getline(ss, item, ',')) {
                config.user_counts.push_back(std::stoi(item));
            }
        } else if (name == "num_servers") {
            config.num_servers = std::stoi(value);
        } else if (name == "load_balancer") {
            if (value == "THERMAL") config.lb_policy = LBPolicy::THERMAL;
            else config.lb_policy = LBPolicy::ROUND_ROBIN;
        } else if (name == "thermal_threshold") {
            config.thermal_threshold = std::stod(value);
        } else if (name == "throttle_factor") {
            config.throttle_factor = std::stod(value);
        }
    }
    return config;
}

int main(int argc, char* argv[]) {
    std::string config_file = "config.txt";
    if (argc > 1) {
        config_file = argv[1];
    }
    Config config = load_config(config_file);

    auto get_dist_name = [](DistributionType d) {
        if (d == DistributionType::CONSTANT) return std::string("CONSTANT");
        if (d == DistributionType::UNIFORM) return std::string("UNIFORM");
        return std::string("EXPONENTIAL");
    };

    std::string s_dist_name = get_dist_name(config.service_dist);
    std::string t_dist_name = get_dist_name(config.think_dist);

    std::cout << "Loading config: " << config_file << std::endl;
    std::cout << "Output directory: " << config.output_dir << std::endl;
    std::cout << "Running experiments with Service: " << s_dist_name 
              << ", Think: " << t_dist_name << " distributions..." << std::endl;
    std::cout << "Users | Avg RT (s) CI (95%) | Thrpt | Goodput | Badput | DropRate | Util | MaxTemp" << std::endl;

    // Initialize CSV with headers in distribution-specific directory
    std::string dir_path = config.output_dir + "/think_time_" + t_dist_name + "/service_time_" + s_dist_name;
    std::filesystem::create_directories(dir_path);
    std::ofstream csv(dir_path + "/des_results.csv");
    csv << "Users,Avg_RT,CI_Half,Throughput,Goodput,Badput,DropRate,Utilization,MaxTemp\n";
    csv.close();

    for (int n : config.user_counts) {
        run_experiment(n, config.num_servers, config.cores, config.threads_per_core, config.ctx_overhead, 
                       config.sim_time, config.warmup, config.mean_think, 
                       config.mean_service, config.timeout, 
                       config.time_slice, config.max_queue_size,
                       config.num_runs, 
                       config.service_dist, config.think_dist, s_dist_name, t_dist_name,
                       config.output_dir, config.lb_policy,
                       config.thermal_threshold, config.throttle_factor);
    }

    return 0;
}
