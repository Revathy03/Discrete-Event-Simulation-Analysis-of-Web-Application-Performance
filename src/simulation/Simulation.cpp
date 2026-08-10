#include "Simulation.h"
#include <iostream>

Simulation::Simulation(int num_users, int num_servers, int num_cores, int threads_per_core, 
                       double ctx_overhead, double end_time, double warmup_time, 
                       double mean_think, double mean_service, double timeout,
                       double quantum, int queue_limit,
                       unsigned int seed, DistributionType s_dist, DistributionType t_dist,
                       LBPolicy lb_policy,
                       double thermal_threshold, double throttle_factor)
    : current_time(0.0),
      end_time(end_time),
      warmup_time(warmup_time),
      metrics(),
      rng(seed),
      mean_think_time(mean_think),
      mean_service_time(mean_service),
      default_timeout(timeout),
      service_dist(s_dist),
      think_dist(t_dist),
      num_servers(num_servers),
      lb_policy(lb_policy),
      lb_rr_index(0),
      next_request_id(0) {
    
    for (int i = 0; i < num_servers; ++i) {
        servers.push_back(new Server(i, num_cores, threads_per_core, ctx_overhead, quantum, queue_limit, [this](Event e) { this->schedule_event(e); }));
        servers.back()->thermal_threshold = thermal_threshold;
        servers.back()->throttle_factor = throttle_factor;
    }

    for (int i = 0; i < num_users; ++i) {
        users.emplace_back(i, mean_think, mean_service, think_dist, service_dist);
    }
}

Simulation::~Simulation() {
    for (auto s : servers) {
        delete s;
    }
}

void Simulation::initialize() {
    // schedule the first think time event for every user to get the simulation started
    for (auto& user : users) {
        user.schedule_next_request(event_queue, rng, current_time);
    }
}

void Simulation::run() {
    bool warmup_cleared = false;
    // core event loop: pull events from the queue and advance current time until end_time is reached
    while (!event_queue.is_empty() && current_time < end_time) {
        Event e = event_queue.pop_event();
        current_time = e.time;
        if (current_time > end_time) break;

        // clear warmup stats when the warmup period ends to ensure steady-state accuracy
        if (!warmup_cleared && current_time >= warmup_time) {
            for (auto server : servers) {
                server->max_observed_temp = server->temperature; // Reset max temp
                for (auto& c : server->cores) {
                    if (c.executing_thread != nullptr) {
                        c.utilization_time = 0.0;
                    } else {
                        c.utilization_time = 0.0;
                    }
                }
            }
            warmup_cleared = true;
        }

        process_event(e);
    }
    metrics.simulation_time = end_time - warmup_time;
}

void Simulation::process_event(const Event& e) {
    // dispatch the event to the appropriate handler based on its type
    switch (e.type) {
        case EventType::THINK_DONE:
            handle_think_done(e);
            break;
        case EventType::REQUEST_ARRIVAL:
            handle_request_arrival(e);
            break;
        case EventType::START_SERVICE:
            handle_start_service(e);
            break;
        case EventType::REQUEST_COMPLETE:
            handle_request_complete(e);
            break;
        case EventType::REQUEST_TIMEOUT:
            handle_request_timeout(e);
            break;
        case EventType::THREAD_PREEMPT:
            servers[e.server_id]->handle_thread_preempt(e.thread_id, current_time);
            break;
    }
}

void Simulation::schedule_event(Event e) {
    event_queue.push_event(e);
}

void Simulation::handle_think_done(const Event& e) {
    int user_id = e.user_id;
    
    // Generate service time based on configuration
    double service_time = rng.generate_service_time(mean_service_time, service_dist); 
    double timeout = default_timeout;
    
    Request* req = new Request(next_request_id++, user_id, current_time, service_time, timeout);
    active_requests[req->id] = req;

    if (current_time >= warmup_time) {
        metrics.record_arrival();
    }

    // Schedule arrival event
    schedule_event(Event(current_time, EventType::REQUEST_ARRIVAL, req->id, user_id));
}

void Simulation::handle_request_arrival(const Event& e) {
    Request* req = active_requests[e.request_id];
    
    // Schedule timeout event
    schedule_event(Event(req->timeout_time, EventType::REQUEST_TIMEOUT, req->id, req->user_id));
    
    Server* chosen_server = nullptr;
    if (lb_policy == LBPolicy::THERMAL) {
        double min_temp = 1e12;
        for (auto s : servers) {
            s->update_temperature(current_time);
            if (s->temperature < min_temp) {
                min_temp = s->temperature;
                chosen_server = s;
            }
        }
    } else { // ROUND_ROBIN
        chosen_server = servers[lb_rr_index];
        lb_rr_index = (lb_rr_index + 1) % servers.size();
    }
    
    chosen_server->handle_request_arrival(req, current_time);
}

void Simulation::handle_start_service(const Event& e) {
    servers[e.server_id]->handle_start_service(e.thread_id, current_time);
}

void Simulation::handle_request_complete(const Event& e) {
    Request* req = active_requests[e.request_id];
    servers[e.server_id]->handle_finish_service(e.thread_id, current_time);

    if (current_time >= warmup_time) {
        if (req->timed_out) {
            metrics.record_badput(req->arrival_time, current_time);
        } else {
            metrics.record_goodput(req->arrival_time, current_time);
        }
    }

    // User is done waiting, schedule next think time
    users[req->user_id].waiting_for_response = false;
    users[req->user_id].schedule_next_request(event_queue, rng, current_time);

    // cleanup the completed request to prevent memory leak

    delete req;
    active_requests.erase(e.request_id);
}

void Simulation::handle_request_timeout(const Event& e) {
    auto it = active_requests.find(e.request_id);
    if (it == active_requests.end()) return; // Already completed

    Request* req = it->second;
    // Find which server it was on? 
    // Wait, REQUEST_TIMEOUT does not have a server_id attached to the original Request. 
    // Let's iterate through all servers and see if it drops.
    for (auto s : servers) {
        s->handle_request_timeout(req, current_time);
    }

    if (req->dropped) {
        if (current_time >= warmup_time) {
            metrics.record_drop();
        }
        // If dropped from queue, user starts thinking again immediately
        users[req->user_id].waiting_for_response = false;
        users[req->user_id].schedule_next_request(event_queue, rng, current_time);
        
        // Delay deletion until Server pops it from the request_queue
        active_requests.erase(it);
    }
    // if req->timed_out (in service), it will be handled by REQUEST_COMPLETE
}
