#ifndef USER_H
#define USER_H

#include "Request.h"
#include "event/EventQueue.h"
#include "utils/RandomGenerator.h"

class User {
public:
    int id;
    bool waiting_for_response;
    double last_request_time;
    double mean_think_time;
    DistributionType think_dist;
    double mean_service_time;
    DistributionType service_dist;

    User(int id, double mean_think, double mean_service, 
         DistributionType t_dist = DistributionType::EXPONENTIAL,
         DistributionType s_dist = DistributionType::EXPONENTIAL);

    void schedule_next_request(EventQueue& eq, RandomGenerator& rg, double current_time);
};

#endif 
