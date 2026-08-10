#include "EventQueue.h"

void EventQueue::push_event(Event e) {
    events.push(e);
}

Event EventQueue::pop_event() {
    Event e = events.top();
    events.pop();
    return e;
}

Event EventQueue::peek_event() const {
    return events.top();
}

bool EventQueue::is_empty() const {
    return events.empty();
}

size_t EventQueue::size() const {
    return events.size();
}
