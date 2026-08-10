#ifndef SIMULATION_H
#define SIMULATION_H

#include <vector>
#include <map>
#include "../event/EventQueue.h"
#include "../user/User.h"
#include "../server/server.h"
#include "../metric/metrics.h"
#include "../utils/RandomGenerator.h"

enum class LBPolicy { ROUND_ROBIN, THERMAL };

class Simulation {
public:
    double current_time;
    double end_time;
    double warmup_time;

    EventQueue event_queue;
    std::vector<User> users;
    std::vector<Server*> servers;
    Metrics metrics;
    RandomGenerator rng;

    double mean_think_time;
    double mean_service_time;
    double default_timeout;
    DistributionType service_dist;
    DistributionType think_dist;

    int num_servers;
    LBPolicy lb_policy;
    int lb_rr_index;

    std::map<int, Request*> active_requests;
    int next_request_id;

    Simulation(int num_users, int num_servers, int num_cores, int threads_per_core, 
               double ctx_overhead, double end_time, double warmup_time, 
               double mean_think, double mean_service, double timeout,
               double time_slice = 1.0, int max_queue_size = -1,
               unsigned int seed = 42,
               DistributionType service_dist = DistributionType::EXPONENTIAL,
               DistributionType think_dist = DistributionType::EXPONENTIAL,
               LBPolicy lb_policy = LBPolicy::ROUND_ROBIN,
               double thermal_threshold = 75.0,
               double throttle_factor = 1.0);
    ~Simulation();

    void initialize();
    void run();
    void process_event(const Event& e);
    void schedule_event(Event e);

private:
    void handle_think_done(const Event& e);
    void handle_request_arrival(const Event& e);
    void handle_start_service(const Event& e);
    void handle_request_complete(const Event& e);
    void handle_request_timeout(const Event& e);
};

#endif
