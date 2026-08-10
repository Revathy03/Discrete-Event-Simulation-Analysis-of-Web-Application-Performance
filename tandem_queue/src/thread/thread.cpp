#include "thread.h"
#include <string>
#include <stdexcept>

Thread::Thread(int id, int core_id)
    : id(id),
      assigned_core(core_id),
      busy(false),
      current_request(nullptr)
{
}

// Reserve thread for a request; caller schedules START_SERVICE
void Thread::assign_request(Request *req)
{
    if (busy)
        throw std::runtime_error("Thread " + std::to_string(id) + " is already busy");
    if (req == nullptr)
        throw std::invalid_argument("Thread::assign_request: null request");

    busy = true;
    current_request = req;
    // assign new request to thread
}

// Free thread after FINISH_SERVICE or a skipped (timed-out) request
void Thread::release()
{
    busy = false;
    current_request = nullptr;
}