#ifndef REQUEST_H
#define REQUEST_H

class Request {
public:
    int id;
    int user_id;
    double arrival_time;
    double service_time;
    double timeout_duration;
    double remaining_service_time;
    double start_service_time;
    double completion_time;
    double timeout_time;
    bool timed_out;
    bool dropped;
    Request(int id, int user_id, double arrival_time, double service_time, double timeout_duration);
};

#endif 
