#include "scheduler.h"

Scheduler::Scheduler(double ctx_overhead)
    : context_switch_overhead(ctx_overhead)
{
}

// enqueue a thread that has just become free
void Scheduler::enqueue(Thread *t)
{
    if (t == nullptr)
        return;
    runnable_threads.push(t);
}

/*round-robin: pop from front, return the thread.
The caller is responsible for calling enqueue() again
when the thread finishes its current request.*/
Thread *Scheduler::schedule_next()
{
    if (runnable_threads.empty())
        return nullptr;
    Thread *t = runnable_threads.front();
    runnable_threads.pop();
    return t;
}

/*returns the fixed context-switch penalty in seconds.
Called by Server::handle_start_service to shift the
effective start time forward before scheduling FINISH_SERVICE.*/
double Scheduler::context_switch()
{
    return context_switch_overhead;
}