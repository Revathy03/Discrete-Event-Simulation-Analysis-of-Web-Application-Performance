#pragma once

class Thread;

class Core
{
public:
    int id;
    bool busy;
    double utilization_time; // cumulative seconds this core was executing
    Thread* executing_thread;

    Core(int id);

    void start_execution(double current_time, int id);
    void finish_execution(double current_time);

    double get_utilization(double sim_duration) const;

private:
    double busy_since; // time the current execution started
};