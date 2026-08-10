#include "Request.h"

Request::Request(int id, int user_id, double arrival_time, double service_time, double timeout_duration)
    : id(id), user_id(user_id), arrival_time(arrival_time), 
      service_time(service_time), timeout_duration(timeout_duration),
      remaining_service_time(service_time),
      timeout_time(arrival_time + timeout_duration), timed_out(false), dropped(false) {}
