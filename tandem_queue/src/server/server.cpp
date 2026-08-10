#include "server.h"
#include <iostream>
#include <iomanip>
#include <stdexcept>



Server::Server(int id,
               int num_cores,
               int threads_per_core,
               double ctx_overhead,
               double quantum,
               int queue_limit,
               std::function<void(Event)> schedule_cb)
    : id(id),
      max_threads(num_cores * threads_per_core),
      context_switch_overhead(ctx_overhead),
      time_slice(quantum),
      max_queue_size(queue_limit),
      schedule_event(schedule_cb),
      rr_index(0)
{
    // build cores and threads with thread-to-core affinity
    int tid = 0;
    for (int cid = 0; cid < num_cores; ++cid)
    {
        cores.emplace_back(cid); // core constructor: Core(int id)
        core_schedulers.emplace_back(ctx_overhead); // Scheduler
        for (int t = 0; t < threads_per_core; ++t)
        {
            threads.emplace_back(tid, cid); // Thread constructor: Thread(int id, int core_id)
            ++tid;
        }
    }
}

/* EVENT: Request arrival

 If a free thread exists - assign it, push START_SERVICE.
 Otherwise - enqueue the request (FCFS).
 Either way timeout is scheduled by the caller
                          (Simulation::handle_request_arrival)
                          so we do NOT schedule it here.*/

void Server::handle_request_arrival(Request *req, double current_time)
{

    Thread *free_t = get_free_thread();

    if (free_t != nullptr)
    {
        assign_thread(free_t, req, current_time);

        // enqueue to the core's ready queue and try to schedule
        core_schedulers[free_t->assigned_core].enqueue(free_t);
        schedule_next_on_core(free_t->assigned_core, current_time);
    }
    else
    {
        // check if queue is full (max_queue_size < 0 means infinite)
        if (max_queue_size >= 0 && (int)request_queue.size() >= max_queue_size)
        {
            req->dropped = true;
            // The simulation/metrics will catch this via handle_request_timeout or arrival metrics
            // but we mark it here so it's not enqueued.
            return;
        }
        request_queue.push(req);
    }
}


//  EVENT: start service

/* Apply context-switch overhead, then schedule FINISH_SERVICE.
 If the request timed out before reaching the CPU, skip it
 and immediately dequeue the next waiting request.*/

void Server::handle_start_service(int thread_id, double current_time)
{
    Thread &t = threads[thread_id];
    Request *req = t.current_request;

    if (req == nullptr)
    {
        throw std::runtime_error("handle_start_service: thread has no request");
    }

    // request timed out while waiting - release thread for next job
    if (req->timed_out || req->dropped)
    {
        cores[t.assigned_core].executing_thread = nullptr;
        free_thread_serve_next(&t, current_time);
        schedule_next_on_core(t.assigned_core, current_time);
        return;
    }

    // record when service actually begins
    if (req->start_service_time < 0.0) {
        req->start_service_time = current_time;
    }
    t.busy = true;

    // context-switch overhead shifts the effective start forward
    double effective_start = current_time + context_switch_overhead;
    double burst = std::min(time_slice, req->remaining_service_time);
    double finish_time = effective_start + burst;


    if (req->remaining_service_time <= time_slice) {
        Event e(finish_time, EventType::REQUEST_COMPLETE, req->id);
        e.thread_id = thread_id;
        e.server_id = id;
        schedule_event(e);
    } else {
        Event e(finish_time, EventType::THREAD_PREEMPT, req->id);
        e.thread_id = thread_id;
        e.server_id = id;
        schedule_event(e);
    }
}

//  EVENT: finish service - request complete
 /*Accumulate core busy time.
 Classify as goodput / badput.
 Release thread; serve next queued request if any.
 Schedule THINK_DONE for the owning user (caller handles
 metrics recording; we just free resources here).*/

 void Server::handle_finish_service(int thread_id, double current_time)
{
    Thread &t = threads[thread_id];
    Request *req = t.current_request;

    if (req == nullptr)
    {
        throw std::runtime_error("handle_finish_service: thread has no request");
    }

    req->completion_time = current_time;

    //accumulate utilization on the pinned core
    double busy_duration = context_switch_overhead + req->remaining_service_time;
    cores[t.assigned_core].utilization_time += busy_duration;
    cores[t.assigned_core].executing_thread = nullptr;
    req->remaining_service_time = 0.0;


    free_thread_serve_next(&t, current_time);
    schedule_next_on_core(t.assigned_core, current_time);
}

void Server::handle_thread_preempt(int thread_id, double current_time)
{
    Thread &t = threads[thread_id];
    Request *req = t.current_request;

    if (req == nullptr)
        throw std::runtime_error("handle_thread_preempt: thread has no request");

    double busy_duration = context_switch_overhead + time_slice;
    cores[t.assigned_core].utilization_time += busy_duration;
    req->remaining_service_time -= time_slice;
    cores[t.assigned_core].executing_thread = nullptr;

    if (req->timed_out || req->dropped)
    {
        free_thread_serve_next(&t, current_time);
    }
    else
    {
        core_schedulers[t.assigned_core].enqueue(&t);
    }

    schedule_next_on_core(t.assigned_core, current_time);
}

 /*EVENT:Request timeout
 Case A - still in queue : remove and mark dropped.
 Case B - in service : mark timed_out so FINISH_SERVICE
                            records it as badput.
 Case C - already finished: ignore (stale timeout event).*/

 void Server::handle_request_timeout(Request *req, double current_time)
{

    // case C: already finished – nothing to do
    if (req->completion_time >= 0.0)
    {
        return;
    }

    // case A: still waiting in queue
    if (req->start_service_time < 0.0)
    {
        // lazy removal: mark dropped; free thread serve next skips it on dequeue
        req->dropped = true;
        return;
    }

    // case B: currently in service
    req->timed_out = true;
}

//  Metrics

double Server::get_avg_core_utilization(double sim_duration) const
{
    if (sim_duration <= 0.0 || cores.empty())
        return 0.0;
    double total = 0.0;
    for (const auto &c : cores)
        total += c.utilization_time;
    return (total / cores.size()) / sim_duration;
}


//  helper code

// round-robin selection among non-busy threads
Thread *Server::get_free_thread()
{
    int n = static_cast<int>(threads.size());
    for (int i = 0; i < n; ++i)
    {
        int idx = (rr_index + i) % n;
        if (!threads[idx].busy)
        {
            rr_index = (idx + 1) % n; // advance pointer for next call
            return &threads[idx];
        }
    }
    return nullptr; // all threads busy
}

// reserve a thread for a request (before START_SERVICE fires)
void Server::assign_thread(Thread *t, Request *req, double current_time)
{
    t->busy = true;
    t->current_request = req;
}

// release thread; if queue has pending requests, serve the next valid one
void Server::free_thread_serve_next(Thread *t, double current_time)
{
    t->busy = false;
    t->current_request = nullptr;

    // drain stale (dropped/timed-out) entries from the front of the queue
    while (!request_queue.empty())
    {
        Request *next = request_queue.front();
        request_queue.pop();

        if (next->dropped || next->timed_out)
        {
            if (next->dropped) delete next; // Safely delete dropped requests here
            // already expired while queued – skip silently
            continue;
        }

        // valid request found: assign and push to the thread's core ready queue
        assign_thread(t, next, current_time);
        core_schedulers[t->assigned_core].enqueue(t);
        // Do NOT call schedule_next_on_core here, the caller handles scheduling.
        return;
    }
    // Queue empty – thread sits idle
}

void Server::schedule_next_on_core(int core_id, double current_time)
{
    if (cores[core_id].executing_thread != nullptr)
        return; // already busy

    Thread *next_t = core_schedulers[core_id].schedule_next();
    if (next_t != nullptr)
    {
        cores[core_id].executing_thread = next_t;
        Event e(current_time, EventType::START_SERVICE, next_t->current_request->id);
        e.thread_id = next_t->id;
        e.server_id = id;
        schedule_event(e);
    }
}