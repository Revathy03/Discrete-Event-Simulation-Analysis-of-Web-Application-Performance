#pragma once
#include <queue>
#include <functional>
#include "../thread/thread.h"
#include "../event/Event.h"

class Scheduler
{
public:
    double context_switch_overhead; // seconds added each time a thread is swapped in

    Scheduler(double ctx_overhead);

    // add a thread to the runnable pool
    void enqueue(Thread *t);

    // pick the next runnable thread (round-robin FCFS order).
    // returns nullptr if no threads are available.
    Thread *schedule_next();

    // returns the time penalty for one context switch (used by Server
    // when computing effective start time of a request).
    double context_switch();

    int queue_depth() const { return static_cast<int>(runnable_threads.size()); }

private:
    std::queue<Thread *> runnable_threads; // FCFS order = round robin
};