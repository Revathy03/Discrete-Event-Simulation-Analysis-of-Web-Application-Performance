#pragma once
#include <vector>
#include <string>

class Metrics
{
public:
    //raw counters
    int completed_requests; // goodput + badput completions
    int goodput_count;      // completed before timeout
    int badput_count;       // completed after timeout deadline
    int dropped_requests;   // timed out while still in queue
    int total_arrivals;

    double total_response_time; // sum over ALL completions
    double simulation_time;     // set at end of run (steady-state window)

    // One entry per completion - used for confidence interval
    std::vector<double> response_samples;

    Metrics();

    // Recording

    // call at REQUEST_COMPLETE for a request that was NOT timed out
    void record_goodput(double arrival_time, double completion_time);

    // call at REQUEST_COMPLETE for a request that WAS timed out (badput)
    void record_badput(double arrival_time, double completion_time);

    // call when a request is removed from the queue due to timeout
    void record_drop();

    // call when a new request arrives (for arrival rate tracking)
    void record_arrival();

    // point estimate metrics
    double compute_avg_response_time() const;
    double compute_throughput() const; // (goodput + badput) / time
    double compute_goodput() const;    // goodput completions / time
    double compute_badput() const;     // badput completions  / time
    double compute_drop_rate() const;  // drops / time

    //confidence interval for avg response time
    // uses the batch-means / independent-runs approach:
    // pass in per-run sample means from multiple independent runs.
    struct ConfidenceInterval
    {
        double mean;
        double half_width; // CI = mean ± half_width
        double lower;
        double upper;
        double std_err;
        int n_runs;
    };

    // Compute 95% CI from a vector of per-run response-time means
    static ConfidenceInterval compute_confidence_interval(
        const std::vector<double> &run_means);

    // Pretty-print all metrics to stdout
    void print_summary() const;

private:
    static double t_critical_95(int df); // t-table lookup for small df
};