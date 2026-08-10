#include "User.h"
#include "event/Event.h"

User::User(int id, double mean_think, double mean_service, DistributionType t_dist, DistributionType s_dist) 
    : id(id), waiting_for_response(false), last_request_time(0.0), 
      mean_think_time(mean_think), think_dist(t_dist), 
      mean_service_time(mean_service), service_dist(s_dist) {}

void User::schedule_next_request(EventQueue& eq, RandomGenerator& rg, double current_time) {
    double think_time = rg.generate_think_time(mean_think_time, think_dist);
    eq.push_event(Event(current_time + think_time, EventType::THINK_DONE, -1, id));
}

