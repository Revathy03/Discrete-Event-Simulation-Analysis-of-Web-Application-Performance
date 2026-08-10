#pragma once
#include <vector>
#include <queue>
#include <functional>
#include "../thread/thread.h"
#include "../core/core.h"
#include "../user/Request.h"
#include "../event/Event.h"
#include "../scheduler/scheduler.h"

class Server
{
public:
    // configuration
    int id;
    int max_threads;
    double context_switch_overhead;
    double time_slice;
    int max_queue_size;

    std::vector<Thread> threads;
    std::vector<Core> cores;
    std::vector<Scheduler> core_schedulers;
    std::queue<Request *> request_queue;

    // callback to push events into the global EventQueue
    std::function<void(Event)> schedule_event;

    Server(int id,
           int num_cores,
           int threads_per_core,
           double ctx_overhead,
           double time_slice,
           int max_queue_size,
           std::function<void(Event)> schedule_cb);

    // primary event handlers (called by Simulation::process_event)
    void handle_request_arrival(Request *req, double current_time);
    void handle_start_service(int thread_id, double current_time);
    void handle_finish_service(int thread_id, double current_time);
    void handle_thread_preempt(int thread_id, double current_time);
    void handle_request_timeout(Request *req, double current_time);

    // metrics helpers
    double get_avg_core_utilization(double sim_duration) const;

private:
    int rr_index; // round-robin pointer

    Thread *get_free_thread();
    void assign_thread(Thread *t, Request *req, double current_time);
    void free_thread_serve_next(Thread *t, double current_time);
    void schedule_next_on_core(int core_id, double current_time);
};