#include "Event.h"

Event::Event(double time, EventType type, int request_id, int user_id, int thread_id, int server_id)
    : time(time), type(type), request_id(request_id), user_id(user_id), thread_id(thread_id), server_id(server_id) {}

bool Event::operator>(const Event& other) const {
    return time > other.time;
}
