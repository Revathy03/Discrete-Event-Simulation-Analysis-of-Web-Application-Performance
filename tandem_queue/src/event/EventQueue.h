#ifndef EVENT_QUEUE_H
#define EVENT_QUEUE_H

#include <queue>
#include <vector>
#include "Event.h"

class EventQueue {
public:
    void push_event(Event e);
    Event pop_event();
    Event peek_event() const;
    bool is_empty() const;
    size_t size() const;

private:
    std::priority_queue<Event, std::vector<Event>, std::greater<Event>> events;
};

#endif 
