#ifndef EVENT_H
#define EVENT_H

#include <string>

enum class EventType {
    REQUEST_ARRIVAL,
    START_SERVICE,
    REQUEST_COMPLETE,
    REQUEST_TIMEOUT,
    THINK_DONE,
    THREAD_PREEMPT
};

class Event {
public:
    double time;
    EventType type;
    int request_id;
    int user_id;
    int thread_id;
    int server_id;

    Event(double time, EventType type, int request_id = -1, int user_id = -1, int thread_id = -1, int server_id = -1);

    bool operator>(const Event& other) const;
};

#endif 
