#ifndef RANDOM_GENERATOR_H
#define RANDOM_GENERATOR_H

#include <random>

enum class DistributionType {
    CONSTANT,
    UNIFORM,
    EXPONENTIAL
};

class RandomGenerator {
public:
    RandomGenerator(unsigned int seed = 42);

    double exponential(double mean);
    double uniform(double a, double b);
    double constant(double value);

    // context specific  (just wrappers)
    double generate_think_time(double mean, DistributionType dist = DistributionType::EXPONENTIAL);
    double generate_service_time(double mean, DistributionType dist = DistributionType::EXPONENTIAL);
    double generate_timeout(double mean_fixed, double mean_variable);

private:
    std::mt19937 rng;
};

#endif 
