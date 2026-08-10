#include "metrics.h"
#include <iostream>
#include <iomanip>
#include <numeric>
#include <cmath>
#include <stdexcept>


Metrics::Metrics()
    : completed_requests(0),
      goodput_count(0),
      badput_count(0),
      dropped_requests(0),
      total_arrivals(0),
      total_response_time(0.0),
      simulation_time(0.0)
{
}


void Metrics::record_arrival()
{
    ++total_arrivals;
}

void Metrics::record_goodput(double arrival_time, double completion_time)
{
    double rt = completion_time - arrival_time;
    ++completed_requests;
    ++goodput_count;
    total_response_time += rt;
    response_samples.push_back(rt);
}

void Metrics::record_badput(double arrival_time, double completion_time)
{
    double rt = completion_time - arrival_time;
    ++completed_requests;
    ++badput_count;
    total_response_time += rt;
    response_samples.push_back(rt);
}

void Metrics::record_drop()
{
    ++dropped_requests;
}

//point estimate metrics
double Metrics::compute_avg_response_time() const
{
    if (completed_requests == 0)
        return 0.0;
    return total_response_time / completed_requests;
}

double Metrics::compute_throughput() const
{
    if (simulation_time <= 0.0)
        return 0.0;
    return static_cast<double>(completed_requests) / simulation_time;
}

double Metrics::compute_goodput() const
{
    if (simulation_time <= 0.0)
        return 0.0;
    return static_cast<double>(goodput_count) / simulation_time;
}

double Metrics::compute_badput() const
{
    if (simulation_time <= 0.0)
        return 0.0;
    return static_cast<double>(badput_count) / simulation_time;
}

double Metrics::compute_drop_rate() const
{
    if (simulation_time <= 0.0)
        return 0.0;
    return static_cast<double>(dropped_requests) / simulation_time;
}

/*  Confidence Interval  (independent runs method)
 Algorithm
 Given R per-run means x1 … xR:
   grand_mean  = (1/R) Σ xi
   sample_var  = (1/(R-1)) Σ (xi - grand_mean)²
   std_err     = sqrt(sample_var / R)
   half_width  = t_{R-1, 0.975} * std_err*/

Metrics::ConfidenceInterval
Metrics::compute_confidence_interval(const std::vector<double> &run_means)
{
    int R = static_cast<int>(run_means.size());
    if (R < 2)
        throw std::invalid_argument("Need at least 2 runs for a confidence interval");

    // Grand mean
    double grand_mean = std::accumulate(run_means.begin(), run_means.end(), 0.0) / R;

    // sample variance of the run means
    double ss = 0.0;
    for (double m : run_means)
    {
        double diff = m - grand_mean;
        ss += diff * diff;
    }
    double sample_var = ss / (R - 1);
    double std_err = std::sqrt(sample_var / R);

    double hw = t_critical_95(R - 1) * std_err;

    return ConfidenceInterval{
        grand_mean,
        hw,
        grand_mean - hw,
        grand_mean + hw,
        std_err,
        R};
}

//  t-table: two-tailed 95% critical values (df 1..30, then inf)
double Metrics::t_critical_95(int df)
{
    // selected values from the t-distribution (two-tailed, alpha=0.05)
    static const double table[] = {
        0,      // index 0 unused
        12.706, // df=1
        4.303,  // df=2
        3.182,  // df=3
        2.776,  // df=4
        2.571,  // df=5
        2.447,  // df=6
        2.365,  // df=7
        2.306,  // df=8
        2.262,  // df=9
        2.228,  // df=10
        2.201,  // df=11
        2.179,  // df=12
        2.160,  // df=13
        2.145,  // df=14
        2.131,  // df=15
        2.120,  // df=16
        2.110,  // df=17
        2.101,  // df=18
        2.093,  // df=19
        2.086,  // df=20
        2.080,  // df=21
        2.074,  // df=22
        2.069,  // df=23
        2.064,  // df=24
        2.060,  // df=25
        2.056,  // df=26
        2.052,  // df=27
        2.048,  // df=28
        2.045,  // df=29
        2.042,  // df=30
    };
    if (df <= 0)
        return 12.706;
    if (df <= 30)
        return table[df];
    // For df > 30 use normal approximation (z = 1.96)
    return 1.96;
}

//  pretty-print summary
void Metrics::print_summary() const
{
    auto w = std::setw(30);
    std::cout << std::fixed << std::setprecision(4);

    std::cout << "  SIMULATION METRICS SUMMARY\n";
    std::cout << w << "Simulation window (s): " << simulation_time << "\n";
    std::cout << w << "Total arrivals: " << total_arrivals << "\n";
    std::cout << w << "Completed (good+bad): " << completed_requests << "\n";
    std::cout << w << "Goodput count: " << goodput_count << "\n";
    std::cout << w << "Badput count: " << badput_count << "\n";
    std::cout << w << "Dropped (queue timeout): " << dropped_requests << "\n\n\n";
    std::cout << w << "Avg response time (s): " << compute_avg_response_time() << "\n";
    std::cout << w << "Throughput (req/s): " << compute_throughput() << "\n";
    std::cout << w << "Goodput (req/s): " << compute_goodput() << "\n";
    std::cout << w << "Badput (req/s): " << compute_badput() << "\n";
    std::cout << w << "Drop rate (req/s): " << compute_drop_rate() << "\n\n";
}