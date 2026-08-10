#pragma once
#include "../user/Request.h"

class Thread
{
public:
    int id;
    int assigned_core; // pinned core (thread-to-core affinity, never changes)
    bool busy;
    Request *current_request;

    Thread(int id, int core_id);

    // assign a request to this thread (marks busy)
    void assign_request(Request *req);

    // release the thread after a request completes or is skipped
    void release();
};