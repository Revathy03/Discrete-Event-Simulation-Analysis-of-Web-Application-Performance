#include "core.h"
#include <stdexcept>
#include <iostream>

using namespace std;

Core::Core(int id)
    : id(id), busy(false), utilization_time(0.0), executing_thread(nullptr), busy_since(-1.0)
{
}

// call when a thread starts executing on this core
void Core::start_execution(double current_time, int id)
{
    // check if this core is already executing something
    if (busy)
        throw runtime_error("Core " + to_string(id) + " already busy");
    busy = true;
    busy_since = current_time;
}

// call when execution finishes; accumulates wall time
void Core::finish_execution(double current_time)
{
    if (!busy)
        throw runtime_error("Core " + to_string(id) + " was not busy");
    utilization_time += (current_time - busy_since);
    busy = false;
    busy_since = -1.0;
}

// returns fraction [0,1] of time the core was busy
double Core::get_utilization(double sim_duration) const
{
    if (sim_duration <= 0.0)
        return 0.0;
    return utilization_time / sim_duration;
}